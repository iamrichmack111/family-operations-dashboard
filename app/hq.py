from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import ipaddress
import json
import math
import re
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from .extensions import db
from .main import role_required
from .models import (
    Chore,
    FamilyEvent,
    FamilyPoll,
    FamilyPollVote,
    FamilyGoal,
    HouseholdAnnouncement,
    Homework,
    ChoreTrade,
    PurchaseRequest,
    ShoppingItem,
    PointTransaction,
    User,
)
from .services import add_points, log_activity, notify, notify_roles, point_balance

bp = Blueprint("hq", __name__)


def _parse_date(value: str | None, *, fallback: date | None = None) -> date | None:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _active_members() -> list[User]:
    return db.session.scalars(
        db.select(User)
        .where(User.active.is_(True), User.role.in_(["manager", "child"]))
        .order_by(User.name)
    ).all()


REWARD_POINTS_PER_DOLLAR = 1
REWARD_MAX_POINTS = 350


class _ProductPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: list[dict[str, str]] = []
        self.in_title = False
        self.title_parts: list[str] = []
        self.json_ld_parts: list[str] = []
        self.in_json_ld = False

    def handle_starttag(self, tag: str, attrs) -> None:
        values = {str(k).lower(): str(v or "") for k, v in attrs}
        if tag.lower() == "meta":
            self.meta.append(values)
        elif tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "script" and "ld+json" in values.get("type", "").lower():
            self.in_json_ld = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() == "script":
            self.in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_json_ld:
            self.json_ld_parts.append(data)


def _safe_product_url(raw_url: str) -> str:
    url = raw_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Paste a complete http:// or https:// product link.")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local-network links cannot be scanned.")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("That store address could not be reached.") from exc
    for result in addresses:
        ip = ipaddress.ip_address(result[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private or local-network product links are not allowed.")
    return url


def _money_value(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", str(value))
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return number if 0.01 <= number <= 100000 else None


def _product_quote(raw_url: str, fallback_price: float | None = None) -> dict:
    url = _safe_product_url(raw_url)
    parsed = urlparse(url)
    title = f"Item from {parsed.hostname.removeprefix('www.')}"
    detected_price = None
    scan_message = "Store price detected automatically."
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(req, timeout=7) as response:
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                raise ValueError("The link did not return a product page.")
            raw = response.read(1_500_000)
        text = raw.decode("utf-8", errors="ignore")
        parser = _ProductPageParser()
        parser.feed(text)

        meta_title = None
        price_candidates: list[float] = []
        for meta in parser.meta:
            key = (meta.get("property") or meta.get("name") or meta.get("itemprop") or "").lower()
            content = unescape(meta.get("content", "")).strip()
            if key in {"og:title", "twitter:title"} and content and not meta_title:
                meta_title = content
            if key in {"product:price:amount", "og:price:amount", "price"}:
                price = _money_value(content)
                if price is not None:
                    price_candidates.append(price)
        page_title = meta_title or unescape(" ".join(parser.title_parts)).strip()
        if page_title:
            title = re.sub(r"\s+", " ", page_title)[:240]

        json_text = " ".join(parser.json_ld_parts)
        for match in re.finditer(r'["\\\']price["\\\']\s*:\s*["\\\']?\$?([0-9][0-9,]*(?:\.[0-9]{1,2})?)', json_text, re.I):
            price = _money_value(match.group(1))
            if price is not None:
                price_candidates.append(price)
        if not price_candidates:
            # Last-resort visible-price pattern. It is intentionally used only
            # after structured product metadata fails.
            for match in re.finditer(r'\$\s*([0-9][0-9,]*(?:\.[0-9]{2})?)', text[:750000]):
                price = _money_value(match.group(1))
                if price is not None:
                    price_candidates.append(price)
                    break
        if price_candidates:
            detected_price = price_candidates[0]
    except Exception as exc:
        scan_message = f"Store scan unavailable ({type(exc).__name__})."

    price = detected_price
    if price is None and fallback_price is not None and fallback_price > 0:
        price = fallback_price
        scan_message = "Store blocked automatic pricing; using the price you entered."
    if price is None:
        return {
            "url": url,
            "title": title,
            "price": None,
            "points": None,
            "message": scan_message + " Enter the displayed item price and check again.",
        }

    points = min(REWARD_MAX_POINTS, max(1, int(math.ceil(price * REWARD_POINTS_PER_DOLLAR))))
    return {
        "url": url,
        "title": title,
        "price": round(price, 2),
        "points": points,
        "message": scan_message,
    }


def _bundle_chores(chore: Chore) -> list[Chore]:
    same_day = db.session.scalars(
        db.select(Chore).where(
            Chore.task_date == chore.task_date,
            Chore.assigned_to == chore.assigned_to,
            Chore.status == "assigned",
        ).order_by(Chore.id)
    ).all()
    name = chore.title.lower()
    if "basement" in name or "laundry" in name:
        return [item for item in same_day if "basement" in item.title.lower() or "laundry" in item.title.lower()]
    if "bathroom" in name or "kitchen deep clean" in name:
        return [item for item in same_day if "bathroom" in item.title.lower() or "kitchen deep clean" in item.title.lower()]
    return [chore]


def _bundle_summary(items: list[Chore]) -> str:
    return " + ".join(re.sub(r"^[^A-Za-z0-9]+\s*", "", item.title).strip() for item in items)


def _trade_chore_options(user_id: int) -> list[dict]:
    chores = db.session.scalars(
        db.select(Chore).where(
            Chore.assigned_to == user_id,
            Chore.status == "assigned",
            Chore.task_date.between(date.today(), date.today() + timedelta(days=7)),
        ).order_by(Chore.task_date, Chore.id)
    ).all()
    pending_ids: set[int] = set()
    for trade in db.session.scalars(db.select(ChoreTrade).where(ChoreTrade.status == "pending")).all():
        pending_ids.update(trade.parsed_chore_ids())
    options = []
    seen: set[int] = set()
    for chore in chores:
        if chore.id in seen or chore.id in pending_ids:
            continue
        bundle = _bundle_chores(chore)
        ids = {item.id for item in bundle}
        seen.update(ids)
        if ids & pending_ids:
            continue
        options.append({"chore": chore, "summary": _bundle_summary(bundle), "count": len(bundle)})
    return options


def _expire_trades() -> None:
    stale = db.session.scalars(
        db.select(ChoreTrade).where(ChoreTrade.status == "pending", ChoreTrade.chore_date < date.today())
    ).all()
    for trade in stale:
        trade.status = "expired"
        trade.resolved_at = datetime.now(timezone.utc)
        add_points(
            trade.offered_by,
            trade.offered_points,
            f"Refund for expired chore trade: {trade.chore_summary}",
            "chore_trade_refund",
            trade.id,
            None,
        )


@bp.get("/planner")
@login_required
def planner():
    start = date.today()
    end = start + timedelta(days=13)

    chore_query = db.select(Chore).where(Chore.task_date.between(start, end)).order_by(Chore.task_date, Chore.id)
    homework_query = db.select(Homework).where(
        Homework.due_date.between(start, end),
        Homework.status.notin_(["archived"]),
    ).order_by(Homework.due_date, Homework.id)

    if current_user.role == "child":
        chore_query = chore_query.where(Chore.assigned_to == current_user.id)
        homework_query = homework_query.where(Homework.assigned_to == current_user.id)

    chores = db.session.scalars(chore_query).all()
    homework = db.session.scalars(homework_query).all()
    events = db.session.scalars(
        db.select(FamilyEvent)
        .where(FamilyEvent.event_date.between(start, end))
        .order_by(FamilyEvent.event_date, FamilyEvent.start_time, FamilyEvent.id)
    ).all()

    chores_by_day: dict[date, list[Chore]] = defaultdict(list)
    homework_by_day: dict[date, list[Homework]] = defaultdict(list)
    events_by_day: dict[date, list[FamilyEvent]] = defaultdict(list)
    for item in chores:
        chores_by_day[item.task_date].append(item)
    for item in homework:
        homework_by_day[item.due_date].append(item)
    for item in events:
        events_by_day[item.event_date].append(item)

    days = []
    for offset in range(14):
        day = start + timedelta(days=offset)
        day_chores = chores_by_day.get(day, [])
        done = sum(1 for item in day_chores if item.status in {"completed", "approved", "excused"})
        days.append(
            {
                "date": day,
                "chores": day_chores,
                "homework": homework_by_day.get(day, []),
                "events": events_by_day.get(day, []),
                "done": done,
                "total": len(day_chores),
                "percent": round(done / len(day_chores) * 100) if day_chores else 0,
            }
        )

    return render_template("planner.html", days=days, members=_active_members())


@bp.post("/planner/events")
@login_required
@role_required("parent", "manager")
def add_event():
    title = request.form.get("title", "").strip()
    event_date = _parse_date(request.form.get("event_date"))
    start_time = request.form.get("start_time", "").strip()[:20]
    category = request.form.get("category", "Family").strip()[:60] or "Family"
    details = request.form.get("details", "").strip()[:1000]

    if not title or not event_date:
        flash("Add a title and date for the calendar item.", "danger")
        return redirect(url_for("hq.planner"))

    item = FamilyEvent(
        title=title[:180],
        event_date=event_date,
        start_time=start_time,
        category=category,
        details=details,
        created_by=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    log_activity(current_user.id, "added calendar item", "family_event", item.id, item.title)
    flash("Calendar item added.", "success")
    return redirect(url_for("hq.planner"))


@bp.post("/planner/events/<int:event_id>/delete")
@login_required
@role_required("parent", "manager")
def delete_event(event_id: int):
    item = db.session.get(FamilyEvent, event_id)
    if item:
        title = item.title
        db.session.delete(item)
        db.session.commit()
        log_activity(current_user.id, "removed calendar item", "family_event", event_id, title)
    return redirect(url_for("hq.planner"))


@bp.get("/household")
@login_required
def household():
    _expire_trades()
    shopping = db.session.scalars(
        db.select(ShoppingItem).order_by(ShoppingItem.done.asc(), ShoppingItem.priority.desc(), ShoppingItem.created_at.desc())
    ).all()
    goals = db.session.scalars(
        db.select(FamilyGoal).order_by(FamilyGoal.status.asc(), FamilyGoal.due_date.asc().nullslast(), FamilyGoal.created_at.desc())
    ).all()

    purchase_query = db.select(PurchaseRequest).where(PurchaseRequest.status != "quoted").order_by(PurchaseRequest.created_at.desc()).limit(60)
    if not current_user.is_parent:
        purchase_query = purchase_query.where(PurchaseRequest.user_id == current_user.id)
    purchases = db.session.scalars(purchase_query).all()

    trade_query = db.select(ChoreTrade).order_by(ChoreTrade.created_at.desc()).limit(80)
    if current_user.role in {"manager", "child"}:
        trade_query = trade_query.where(
            or_(
                ChoreTrade.offered_by == current_user.id,
                ChoreTrade.requested_to == current_user.id,
                ChoreTrade.accepted_by == current_user.id,
                and_(ChoreTrade.requested_to.is_(None), ChoreTrade.status == "pending"),
            )
        )
    trades = db.session.scalars(trade_query).all()

    members = _active_members()
    balances = {member.id: point_balance(member.id) for member in members}
    open_shopping = sum(1 for item in shopping if not item.done)
    active_goals = sum(1 for item in goals if item.status == "active")
    pending_rewards = sum(1 for item in purchases if item.status == "pending")
    pending_trades = sum(1 for item in trades if item.status == "pending")
    reward_quote = None
    quote_id = session.get("reward_quote_id")
    if quote_id and current_user.role in {"manager", "child"}:
        quote_item = db.session.get(PurchaseRequest, int(quote_id))
        if quote_item and quote_item.user_id == current_user.id and quote_item.status == "quoted":
            reward_quote = {
                "title": quote_item.product_title,
                "price": quote_item.price_dollars,
                "points": quote_item.cost_points,
                "message": "Point quote ready. The product link is stored privately for parent review.",
            }
        else:
            session.pop("reward_quote_id", None)
    chore_options = _trade_chore_options(current_user.id) if current_user.role in {"manager", "child"} else []

    announcements = db.session.scalars(
        db.select(HouseholdAnnouncement)
        .where(
            HouseholdAnnouncement.active.is_(True),
            or_(HouseholdAnnouncement.expires_on.is_(None), HouseholdAnnouncement.expires_on >= date.today()),
        )
        .order_by(HouseholdAnnouncement.pinned.desc(), HouseholdAnnouncement.priority.desc(), HouseholdAnnouncement.created_at.desc())
        .limit(12)
    ).all()
    polls = db.session.scalars(
        db.select(FamilyPoll).order_by(FamilyPoll.status.asc(), FamilyPoll.created_at.desc()).limit(8)
    ).all()
    poll_cards = []
    for poll in polls:
        options = poll.options()
        counts = [0 for _ in options]
        my_vote = None
        for vote in poll.votes:
            if 0 <= vote.choice_index < len(counts):
                counts[vote.choice_index] += 1
            if vote.user_id == current_user.id:
                my_vote = vote.choice_index
        total_votes = sum(counts)
        poll_cards.append({
            "poll": poll,
            "options": options,
            "counts": counts,
            "total_votes": total_votes,
            "my_vote": my_vote,
        })

    week_start = date.today() - timedelta(days=6)
    scorecards = []
    for member in members:
        assigned = int(db.session.scalar(
            db.select(func.count(Chore.id)).where(Chore.assigned_to == member.id, Chore.task_date.between(week_start, date.today()))
        ) or 0)
        finished = int(db.session.scalar(
            db.select(func.count(Chore.id)).where(
                Chore.assigned_to == member.id,
                Chore.task_date.between(week_start, date.today()),
                Chore.status.in_(["completed", "approved", "excused"]),
            )
        ) or 0)
        net_points = int(db.session.scalar(
            db.select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(
                PointTransaction.user_id == member.id,
                PointTransaction.created_at >= datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc),
            )
        ) or 0)
        scorecards.append({
            "member": member,
            "assigned": assigned,
            "finished": finished,
            "percent": round(finished / assigned * 100) if assigned else 100,
            "net_points": net_points,
            "balance": balances.get(member.id, 0),
        })

    return render_template(
        "household.html",
        shopping=shopping,
        goals=goals,
        purchases=purchases,
        trades=trades,
        members=members,
        balances=balances,
        chore_options=chore_options,
        reward_quote=reward_quote,
        reward_max_points=REWARD_MAX_POINTS,
        reward_points_per_dollar=REWARD_POINTS_PER_DOLLAR,
        announcements=announcements,
        poll_cards=poll_cards,
        scorecards=scorecards,
        open_shopping=open_shopping,
        active_goals=active_goals,
        pending_rewards=pending_rewards,
        pending_trades=pending_trades,
        today=date.today(),
    )


@bp.post("/household/announcements/add")
@login_required
@role_required("parent", "manager")
def announcement_add():
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title:
        flash("Announcement title is required.", "danger")
        return redirect(url_for("hq.household") + "#bulletin")
    priority = request.form.get("priority", "normal").strip().lower()
    if priority not in {"normal", "important", "urgent"}:
        priority = "normal"
    item = HouseholdAnnouncement(
        title=title[:180],
        body=body[:1500],
        priority=priority,
        pinned=bool(request.form.get("pinned")),
        expires_on=_parse_date(request.form.get("expires_on")),
        created_by=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    log_activity(current_user.id, "posted household announcement", "announcement", item.id, item.title)
    flash("Announcement posted.", "success")
    return redirect(url_for("hq.household") + "#bulletin")


@bp.post("/household/announcements/<int:announcement_id>/archive")
@login_required
@role_required("parent", "manager")
def announcement_archive(announcement_id: int):
    item = db.session.get(HouseholdAnnouncement, announcement_id)
    if item:
        item.active = False
        db.session.commit()
        log_activity(current_user.id, "archived household announcement", "announcement", item.id, item.title)
    return redirect(url_for("hq.household") + "#bulletin")


@bp.post("/household/polls/create")
@login_required
@role_required("parent", "manager")
def poll_create():
    question = request.form.get("question", "").strip()
    options = [value.strip() for value in request.form.get("options", "").splitlines() if value.strip()]
    if not question or len(options) < 2:
        flash("Add a poll question and at least two choices, one per line.", "danger")
        return redirect(url_for("hq.household") + "#polls")
    poll = FamilyPoll(
        question=question[:240],
        options_json=json.dumps(options[:8]),
        created_by=current_user.id,
        closes_on=_parse_date(request.form.get("closes_on")),
    )
    db.session.add(poll)
    db.session.commit()
    log_activity(current_user.id, "created family poll", "family_poll", poll.id, poll.question)
    return redirect(url_for("hq.household") + "#polls")


@bp.post("/household/polls/<int:poll_id>/vote")
@login_required
def poll_vote(poll_id: int):
    poll = db.session.get(FamilyPoll, poll_id)
    choice = request.form.get("choice", type=int)
    if not poll or poll.status != "open" or (poll.closes_on and poll.closes_on < date.today()):
        flash("That poll is closed.", "warning")
        return redirect(url_for("hq.household") + "#polls")
    options = poll.options()
    if choice is None or choice < 0 or choice >= len(options):
        flash("Choose one of the poll options.", "danger")
        return redirect(url_for("hq.household") + "#polls")
    vote = db.session.scalar(db.select(FamilyPollVote).where(FamilyPollVote.poll_id == poll.id, FamilyPollVote.user_id == current_user.id))
    if vote:
        vote.choice_index = choice
    else:
        db.session.add(FamilyPollVote(poll_id=poll.id, user_id=current_user.id, choice_index=choice))
    db.session.commit()
    log_activity(current_user.id, "voted in family poll", "family_poll", poll.id, poll.question)
    return redirect(url_for("hq.household") + "#polls")


@bp.post("/household/polls/<int:poll_id>/close")
@login_required
@role_required("parent", "manager")
def poll_close(poll_id: int):
    poll = db.session.get(FamilyPoll, poll_id)
    if poll:
        poll.status = "closed"
        db.session.commit()
        log_activity(current_user.id, "closed family poll", "family_poll", poll.id, poll.question)
    return redirect(url_for("hq.household") + "#polls")


@bp.post("/household/shopping/add")
@login_required
def shopping_add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Enter an item first.", "danger")
        return redirect(url_for("hq.household") + "#shopping")
    item = ShoppingItem(
        title=title[:180],
        quantity=(request.form.get("quantity", "1").strip() or "1")[:40],
        category=(request.form.get("category", "Household").strip() or "Household")[:60],
        priority=max(1, min(3, request.form.get("priority", type=int) or 1)),
        added_by=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    log_activity(current_user.id, "added shopping item", "shopping", item.id, item.title)
    return redirect(url_for("hq.household") + "#shopping")


@bp.post("/household/shopping/<int:item_id>/toggle")
@login_required
def shopping_toggle(item_id: int):
    item = db.session.get(ShoppingItem, item_id)
    if item:
        item.done = not item.done
        item.done_by = current_user.id if item.done else None
        item.done_at = datetime.now(timezone.utc) if item.done else None
        db.session.commit()
        log_activity(current_user.id, "checked shopping item" if item.done else "reopened shopping item", "shopping", item.id, item.title)
    return redirect(url_for("hq.household") + "#shopping")


@bp.post("/household/shopping/<int:item_id>/delete")
@login_required
def shopping_delete(item_id: int):
    item = db.session.get(ShoppingItem, item_id)
    if item and (current_user.role in {"parent", "manager"} or item.added_by == current_user.id):
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("hq.household") + "#shopping")


@bp.post("/household/goals/add")
@login_required
@role_required("parent", "manager")
def goal_add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Goal title is required.", "danger")
        return redirect(url_for("hq.household") + "#goals")

    target = max(1, request.form.get("target_value", type=int) or 1)
    assignee_id = request.form.get("assigned_to", type=int)
    if assignee_id and not db.session.get(User, assignee_id):
        assignee_id = None
    goal = FamilyGoal(
        title=title[:180],
        description=request.form.get("description", "").strip()[:1000],
        target_value=target,
        current_value=0,
        unit=(request.form.get("unit", "steps").strip() or "steps")[:40],
        due_date=_parse_date(request.form.get("due_date")),
        assigned_to=assignee_id,
        created_by=current_user.id,
    )
    db.session.add(goal)
    db.session.commit()
    log_activity(current_user.id, "created family goal", "family_goal", goal.id, goal.title)
    flash("Goal created.", "success")
    return redirect(url_for("hq.household") + "#goals")


@bp.post("/household/goals/<int:goal_id>/progress")
@login_required
def goal_progress(goal_id: int):
    goal = db.session.get(FamilyGoal, goal_id)
    if not goal or goal.status != "active":
        return redirect(url_for("hq.household") + "#goals")
    if goal.assigned_to and goal.assigned_to != current_user.id and current_user.role not in {"parent", "manager"}:
        flash("That goal belongs to another family member.", "danger")
        return redirect(url_for("hq.household") + "#goals")

    amount = request.form.get("amount", type=int) or 1
    goal.current_value = max(0, min(goal.target_value, goal.current_value + amount))
    if goal.current_value >= goal.target_value:
        goal.status = "completed"
        goal.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    log_activity(current_user.id, "updated family goal", "family_goal", goal.id, f"{goal.title}: {goal.current_value}/{goal.target_value}")
    return redirect(url_for("hq.household") + "#goals")


@bp.post("/household/goals/<int:goal_id>/delete")
@login_required
@role_required("parent")
def goal_delete(goal_id: int):
    goal = db.session.get(FamilyGoal, goal_id)
    if goal:
        db.session.delete(goal)
        db.session.commit()
    return redirect(url_for("hq.household") + "#goals")


@bp.post("/household/rewards/quote")
@login_required
def reward_quote():
    if current_user.role not in {"manager", "child"}:
        flash("Parent accounts review purchase requests instead of redeeming them.", "warning")
        return redirect(url_for("hq.household") + "#rewards")
    raw_url = request.form.get("product_url", "").strip()
    fallback = request.form.get("fallback_price", type=float)
    try:
        quote = _product_quote(raw_url, fallback)
    except ValueError as exc:
        session.pop("reward_quote_id", None)
        flash(str(exc), "danger")
        return redirect(url_for("hq.household") + "#rewards")

    # Never put the raw product URL in Flask's client-side session cookie.
    # A successful quote is stored server-side and the browser receives only
    # the internal database ID.
    old_quotes = db.session.scalars(
        db.select(PurchaseRequest).where(
            PurchaseRequest.user_id == current_user.id,
            PurchaseRequest.status == "quoted",
        )
    ).all()
    for old in old_quotes:
        db.session.delete(old)
    session.pop("reward_quote_id", None)

    if quote["points"] is None:
        db.session.commit()
        flash(quote["message"] + " Re-paste the product link with the displayed price.", "warning")
        return redirect(url_for("hq.household") + "#rewards")

    item = PurchaseRequest(
        user_id=current_user.id,
        product_url=quote["url"][:2000],
        product_title=(quote.get("title") or "Requested item")[:240],
        price_cents=int(round(float(quote["price"]) * 100)) if quote.get("price") is not None else None,
        cost_points=int(quote["points"]),
        status="quoted",
        note="",
    )
    db.session.add(item)
    db.session.commit()
    session["reward_quote_id"] = item.id
    flash(f"Point quote ready: {item.cost_points} points.", "success")
    return redirect(url_for("hq.household") + "#rewards")


@bp.post("/household/rewards/request")
@login_required
def reward_request():
    if current_user.role not in {"manager", "child"}:
        flash("Parent accounts review purchase requests instead of redeeming them.", "warning")
        return redirect(url_for("hq.household") + "#rewards")
    quote_id = session.get("reward_quote_id")
    item = db.session.get(PurchaseRequest, int(quote_id)) if quote_id else None
    if not item or item.user_id != current_user.id or item.status != "quoted":
        session.pop("reward_quote_id", None)
        flash("Check the product link first to get a valid point quote.", "danger")
        return redirect(url_for("hq.household") + "#rewards")
    points = int(item.cost_points or 0)
    if points <= 0 or points > REWARD_MAX_POINTS:
        flash("That quote is no longer valid.", "danger")
        return redirect(url_for("hq.household") + "#rewards")
    if point_balance(current_user.id) < points:
        flash("You do not have enough points for this item.", "warning")
        return redirect(url_for("hq.household") + "#rewards")

    item.status = "pending"
    item.note = request.form.get("note", "").strip()[:1000]
    db.session.flush()
    add_points(
        current_user.id,
        -points,
        f"Purchase request escrow: {item.product_title}",
        "purchase_request",
        item.id,
        current_user.id,
    )
    session.pop("reward_quote_id", None)
    notify_roles(
        {"parent"},
        "🛍️",
        f"New purchase request from {current_user.name}",
        f"{item.product_title} · {points} points",
        url_for("hq.household") + "#rewards",
    )
    log_activity(current_user.id, "submitted purchase request", "purchase_request", item.id, f"{item.product_title} · {points} points")
    flash("Purchase request sent for parent review.", "success")
    return redirect(url_for("hq.household") + "#rewards")


@bp.post("/household/purchases/<int:purchase_id>/resolve")
@login_required
@role_required("parent")
def purchase_resolve(purchase_id: int):
    item = db.session.get(PurchaseRequest, purchase_id)
    status = request.form.get("status", "")
    if not item or item.status != "pending" or status not in {"fulfilled", "denied"}:
        flash("Invalid purchase update.", "danger")
        return redirect(url_for("hq.household") + "#rewards")
    item.status = status
    item.resolved_by = current_user.id
    item.resolved_at = datetime.now(timezone.utc)
    if status == "denied":
        add_points(
            item.user_id,
            item.cost_points,
            f"Refund for denied purchase: {item.product_title}",
            "purchase_refund",
            item.id,
            current_user.id,
        )
    else:
        db.session.commit()
    notify(
        item.user_id,
        "🛍️",
        f"Purchase request {status}",
        item.product_title,
        url_for("hq.household") + "#rewards",
    )
    log_activity(current_user.id, f"{status} purchase request", "purchase_request", item.id, item.product_title)
    return redirect(url_for("hq.household") + "#rewards")


@bp.post("/household/chore-trades/create")
@login_required
def chore_trade_create():
    if current_user.role not in {"manager", "child"}:
        flash("Only household members with chore assignments can post trades.", "warning")
        return redirect(url_for("hq.household") + "#trades")
    chore_id = request.form.get("chore_id", type=int)
    offered_points = request.form.get("offered_points", type=int) or 0
    requested_to = request.form.get("requested_to", type=int)
    chore = db.session.get(Chore, chore_id) if chore_id else None
    if not chore or chore.assigned_to != current_user.id or chore.status != "assigned" or chore.task_date < date.today():
        flash("That chore is no longer available to trade.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    if offered_points <= 0:
        flash("Offer at least 1 point for the trade.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    if point_balance(current_user.id) < offered_points:
        flash("You do not have enough points to place that offer in escrow.", "warning")
        return redirect(url_for("hq.household") + "#trades")

    if requested_to:
        requested = db.session.get(User, requested_to)
        if not requested or not requested.active or requested.role not in {"manager", "child"} or requested.id == current_user.id:
            flash("Choose another eligible household member or leave the trade open.", "danger")
            return redirect(url_for("hq.household") + "#trades")

    bundle = _bundle_chores(chore)
    bundle_ids = {item.id for item in bundle}
    for trade in db.session.scalars(db.select(ChoreTrade).where(ChoreTrade.status == "pending")).all():
        if bundle_ids & set(trade.parsed_chore_ids()):
            flash("One of those chores already has an open trade.", "warning")
            return redirect(url_for("hq.household") + "#trades")

    trade = ChoreTrade(
        offered_by=current_user.id,
        requested_to=requested_to,
        chore_ids=",".join(str(item.id) for item in bundle),
        chore_date=chore.task_date,
        chore_summary=_bundle_summary(bundle)[:400],
        offered_points=offered_points,
        note=request.form.get("note", "").strip()[:1000],
    )
    db.session.add(trade)
    db.session.flush()
    add_points(
        current_user.id,
        -offered_points,
        f"Chore trade escrow: {trade.chore_summary}",
        "chore_trade_escrow",
        trade.id,
        current_user.id,
    )
    if requested_to:
        notify(requested_to, "🔄", f"Chore trade offer from {current_user.name}", f"{trade.chore_summary} · {offered_points} points", url_for("hq.household") + "#trades")
    log_activity(current_user.id, "posted chore trade", "chore_trade", trade.id, f"{trade.chore_summary} · {offered_points} points")
    flash("Trade posted. Your offered points are safely held in escrow.", "success")
    return redirect(url_for("hq.household") + "#trades")


@bp.post("/household/chore-trades/<int:trade_id>/accept")
@login_required
def chore_trade_accept(trade_id: int):
    if current_user.role not in {"manager", "child"}:
        flash("Only household members with chore assignments can accept trades.", "warning")
        return redirect(url_for("hq.household") + "#trades")
    trade = db.session.get(ChoreTrade, trade_id)
    if not trade or trade.status != "pending" or trade.offered_by == current_user.id:
        flash("That trade is no longer available.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    if trade.requested_to and trade.requested_to != current_user.id:
        flash("That offer was made to someone else.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    if trade.chore_date < date.today():
        flash("That chore date has already passed.", "danger")
        return redirect(url_for("hq.household") + "#trades")

    chores = [db.session.get(Chore, item_id) for item_id in trade.parsed_chore_ids()]
    if not chores or any(item is None or item.status != "assigned" or item.assigned_to != trade.offered_by for item in chores):
        trade.status = "canceled"
        trade.resolved_at = datetime.now(timezone.utc)
        add_points(trade.offered_by, trade.offered_points, f"Refund for unavailable chore trade: {trade.chore_summary}", "chore_trade_refund", trade.id, None)
        flash("The assignment changed, so the trade was canceled and refunded.", "warning")
        return redirect(url_for("hq.household") + "#trades")

    for item in chores:
        item.assigned_to = current_user.id
        item.reassignment_reason = f"Chore trade accepted from {trade.offerer.name} for {trade.offered_points} points."
    trade.status = "accepted"
    trade.accepted_by = current_user.id
    trade.resolved_at = datetime.now(timezone.utc)
    add_points(
        current_user.id,
        trade.offered_points,
        f"Accepted chore trade: {trade.chore_summary}",
        "chore_trade_payment",
        trade.id,
        trade.offered_by,
    )
    notify(trade.offered_by, "✅", f"{current_user.name} accepted your chore trade", f"{trade.chore_summary} · {trade.offered_points} points", url_for("hq.household") + "#trades")
    log_activity(current_user.id, "accepted chore trade", "chore_trade", trade.id, f"{trade.chore_summary} · {trade.offered_points} points")
    flash(f"Trade accepted. {trade.offered_points} points were transferred to you.", "success")
    return redirect(url_for("hq.household") + "#trades")


@bp.post("/household/chore-trades/<int:trade_id>/cancel")
@login_required
def chore_trade_cancel(trade_id: int):
    trade = db.session.get(ChoreTrade, trade_id)
    if not trade or trade.status != "pending":
        flash("That trade cannot be canceled.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    allowed = current_user.is_parent or current_user.id == trade.offered_by or (trade.requested_to and current_user.id == trade.requested_to)
    if not allowed:
        flash("You cannot cancel that trade.", "danger")
        return redirect(url_for("hq.household") + "#trades")
    trade.status = "declined" if trade.requested_to == current_user.id and current_user.id != trade.offered_by else "canceled"
    trade.resolved_at = datetime.now(timezone.utc)
    add_points(
        trade.offered_by,
        trade.offered_points,
        f"Refund for {trade.status} chore trade: {trade.chore_summary}",
        "chore_trade_refund",
        trade.id,
        current_user.id,
    )
    if trade.offered_by != current_user.id:
        notify(trade.offered_by, "↩️", f"Chore trade {trade.status}", trade.chore_summary, url_for("hq.household") + "#trades")
    log_activity(current_user.id, f"{trade.status} chore trade", "chore_trade", trade.id, trade.chore_summary)
    flash("Trade closed and the escrowed points were refunded.", "success")
    return redirect(url_for("hq.household") + "#trades")
