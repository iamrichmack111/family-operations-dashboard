#!/usr/bin/env python3
"""Restore exact balances with an auditable delta, once, against the live SQLite database.
Usage: python restore_points.py --database instance/family_dashboard.db --apply
Stop the app first to avoid conflicts, and restart it after applying.
"""
import argparse
import datetime
import sqlite3
from pathlib import Path

TARGETS = {"Jasmin": 120289, "Aria": 14000}
MARKER = "balance_restore_20261019_fruit50_corrected_14000"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, default=Path("instance/family_dashboard.db"))
    p.add_argument("--apply", action="store_true", help="Back up database and apply one-time adjustments")
    args = p.parse_args()
    dbfile = args.database.expanduser().resolve()
    if not dbfile.is_file():
        p.error(f"Database not found: {dbfile}")
    conn = sqlite3.connect(str(dbfile), timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE" if args.apply else "BEGIN")
        rows=[]
        for name,target in TARGETS.items():
            people=conn.execute("SELECT id FROM users WHERE name = ? COLLATE NOCASE",(name,)).fetchall()
            if len(people)!=1:
                raise RuntimeError(f"Expected exactly one account named {name}; found {len(people)}")
            uid=people[0]["id"]
            current=conn.execute("SELECT COALESCE(SUM(amount), 0) FROM point_transactions WHERE user_id=?",(uid,)).fetchone()[0]
            already=conn.execute("SELECT COUNT(*) FROM point_transactions WHERE user_id=? AND source_type=? AND reason LIKE ?",(uid,MARKER,f"Restore {name} balance%" )).fetchone()[0]
            rows.append((name,uid,current,target,target-current,already))
        for name,uid,current,target,delta,already in rows:
            print(f"{name}: current={current:,}, target={target:,}, adjustment={delta:+,}, previously_restored={bool(already)}")
        if not args.apply:
            print("Preview only. Run with --apply to make changes.")
            return
        if any(r[5] for r in rows):
            print("The corrected restore has already run: no changes applied.")
            return
        stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup=dbfile.with_name(f"{dbfile.stem}-before-fruit50-{stamp}.db")
        # SQLite online backup safely snapshots the open transaction's original database.
        # Release transaction before backup; re-read under write lock afterward.
        conn.rollback()
        with sqlite3.connect(str(dbfile), timeout=20) as source, sqlite3.connect(str(backup)) as dest:
            source.backup(dest)
        print(f"Backup: {backup}")
        conn.execute("BEGIN IMMEDIATE")
        for name,uid,old,target,delta,already in rows:
            now=conn.execute("SELECT COALESCE(SUM(amount),0) FROM point_transactions WHERE user_id=?",(uid,)).fetchone()[0]
            prior=conn.execute("SELECT COUNT(*) FROM point_transactions WHERE user_id=? AND source_type=?",(uid,MARKER)).fetchone()[0]
            if prior: raise RuntimeError(f"Already restored: {name}")
            if now!=old: raise RuntimeError(f"Balance changed during backup for {name}; retry")
            if delta:
                conn.execute("INSERT INTO point_transactions (user_id,amount,reason,source_type,source_id,created_by,reversal_of_id,money_rate,created_at) VALUES (?,?,?,?,NULL,NULL,NULL,0,?)",(uid,delta,f"Restore {name} balance to {target:,}",MARKER,datetime.datetime.now(datetime.timezone.utc).isoformat()))
        conn.commit()
        print("Balances restored. Existing point history retained.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__": main()
