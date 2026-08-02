from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DateField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    user_id = SelectField("Account", coerce=int, validators=[DataRequired()])
    password = PasswordField("PIN", validators=[DataRequired(), Length(min=4, max=32)])
    remember = BooleanField("Remember me")
    submit = SubmitField("🔐 Sign in")


class PinForm(FlaskForm):
    user_id = SelectField("User", coerce=int, validators=[DataRequired()])
    pin = PasswordField("New PIN", validators=[DataRequired(), Length(min=4, max=32)])
    confirm_pin = PasswordField("Confirm PIN", validators=[DataRequired(), EqualTo("pin")])
    submit = SubmitField("🔑 Update PIN")


class MessageForm(FlaskForm):
    recipient_id = SelectField("To", coerce=int, validators=[DataRequired()])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=180)])
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField("💬 Send message")


class GrievanceForm(FlaskForm):
    subject = StringField("Subject", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Explanation", validators=[DataRequired(), Length(max=8000)])
    submit = SubmitField("🔒 Submit privately")


class HomeworkForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=180)])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=100)])
    assigned_to = SelectField("Assign to", coerce=str, validators=[DataRequired()])
    due_date = DateField("Due date", validators=[DataRequired()])
    points = IntegerField("Points", default=5, validators=[DataRequired(), NumberRange(min=0, max=10000)])
    recurring = SelectField("Repeat", choices=[("none", "One time"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")])
    details = TextAreaField("Details", validators=[Optional(), Length(max=8000)])
    attachment = FileField("Attachment", validators=[Optional(), FileAllowed(["pdf", "png", "jpg", "jpeg", "txt", "docx"], "Unsupported file type")])
    submit = SubmitField("📚 Assign homework")


class ViolationForm(FlaskForm):
    subject_user_id = SelectField("Person", coerce=int, validators=[DataRequired()])
    incident_date = DateField("Incident date", validators=[DataRequired()])
    categories = SelectMultipleField("Subjects", coerce=int, validators=[DataRequired()])
    explanation = TextAreaField("Explanation", validators=[DataRequired(), Length(max=12000)])
    evidence_notes = TextAreaField("Evidence or notes", validators=[Optional(), Length(max=8000)])
    attachment = FileField("Evidence attachment", validators=[Optional(), FileAllowed(["pdf", "png", "jpg", "jpeg", "txt"], "Unsupported file type")])
    points_deducted = IntegerField("Points deducted", default=5, validators=[DataRequired(), NumberRange(min=0, max=100000)])
    submit = SubmitField("⚠️ Issue violation")


class PointAdjustmentForm(FlaskForm):
    user_id = SelectField("User", coerce=int, validators=[DataRequired()])
    amount = IntegerField("Point adjustment", validators=[DataRequired(), NumberRange(min=-100000, max=100000)])
    reason = StringField("Reason", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("⭐ Update points")


class MoneyRateForm(FlaskForm):
    money_per_point = StringField("Dollars per point", validators=[DataRequired()])
    submit = SubmitField("💵 Save conversion rate")


class NewUserForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(min=2, max=80)],
    )

    role = SelectField(
        "Role",
        choices=[
            ("parent", "👑 Parent"),
            ("manager", "🗝️ House manager"),
            ("child", "🌟 Child"),
        ],
        validators=[DataRequired()],
    )

    pin = PasswordField(
        "Temporary PIN",
        validators=[DataRequired(), Length(min=4, max=32)],
    )

    confirm_pin = PasswordField(
        "Confirm PIN",
        validators=[DataRequired(), EqualTo("pin")],
    )

    submit = SubmitField("➕ Add family member")


class FamilyPostForm(FlaskForm):
    message = TextAreaField(
        "Family update",
        validators=[DataRequired(), Length(min=1, max=2000)],
    )

    submit = SubmitField("📣 Post to Family News")
