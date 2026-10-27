from django import forms

from .models import Profile


TIMEZONE_CHOICES = [
    ("UTC", "UTC (UTC+0)"),
    ("EST", "EST (UTC-5)"),
    ("CST", "CST (UTC-6)"),
    ("MST", "MST (UTC-7)"),
    ("PST", "PST (UTC-8)"),
]

SKILL_CHOICES = [
    (skill, skill)
    for skill in [
        "Academic tutoring",
        "Active listening",
        "Communication",
        "Critical thinking",
        "Data analysis",
        "Graphic design",
        "Leadership",
        "Mathematics",
        "Microsoft Office",
        "Organization",
        "Peer mentoring",
        "Presentation",
        "Problem solving",
        "Programming",
        "Project management",
        "Research",
        "Social media",
        "Teamwork",
        "Time management",
        "Writing",
    ]
]

COURSE_CHOICES = [
    (course, f"{course} — {name}")
    for course, name in [
        ("ENG 1005", "Writing About Topics"),
        ("ENG 1130", "Introduction to Literary Studies"),
        ("HON 1700", "Hot Topics in Today's World"),
        ("COM 1500", "Speak for Success"),
        ("COM 2250", "Interpersonal Communication"),
        ("ENG 2005", "Speaking of Literature"),
        ("HON 1701", "Discourse and Social Issues"),
        ("BIO 1942", "SCUBA Certification & Ocean Appreciation"),
        ("DPT 2000", "Strategic Resilience Building Strength for Life"),
        ("EDU 2661", "SELF Social Emotional Learning Foundation"),
        ("EXS 2200", "Applying Ancient Wellness Traditions to Modern Wellbeing"),
        ("FIN 1105", "Personal Finance"),
        ("MUS 1162", "Music and Wellness"),
        ("PED 1005", "Resilience in Physical Wellness"),
        ("PSY 1700", "Psychological Well-Being and Resilience"),
        ("CRM 1280", "Intro to Criminal Justice"),
        ("ECO 2205", "Principles of Microeconomics"),
        ("EDU 2100", "Schools and Society"),
        ("HIS 2215", "American Experience Through the Civil War"),
        ("HIS 2225", "American Experience Since the Civil War"),
        ("POS 2100", "Introductory Colloquium in Political Science"),
        ("POS 2410", "Introduction to Public Administration and Public Service"),
        ("POS 2900", "Introduction to International Relations"),
        ("PSY 1106", "Psychology in the Social World"),
        ("SOC 1100", "Intro to Sociology"),
        ("ART 1175", "History of Game Design"),
        ("COM 2100", "Mass Media and Society"),
        ("COM 2280", "Gender, Race, Class & Media"),
        ("ECO 2207", "Principles of Macroeconomics"),
        ("ENG 2360", "Special Topics in Race, Ethnicity, and Literature"),
        ("HIS 1100", "The Ancient World"),
        ("HIS 1200", "Making of the Modern World"),
        ("HIS 1300", "The Modern World"),
        ("MUS 1166", "Caribbean Music"),
        ("PSY 1879", "Global Transformations Within Psychological Science"),
        ("REL/PHI 2219", "World Religions and Philosophies"),
        ("SPA 1101", "First Semester Spanish"),
        ("SPA 2205", "Conversation & Composition I"),
        ("WST 2200", "Intro to Women and Gender Studies"),
        ("ARH 2500", "Introduction to Museum Studies"),
        ("COM 2270", "Intercultural Communication"),
        ("EDU 2105", "Philosophy of Education"),
        ("ENG 2305", "Masterpieces of World Literature"),
        ("ENG 2310", "American Literature II, 1865-Present"),
        ("ENG 2370", "Gender in Literature"),
        ("PHI 2204", "Ethics"),
        ("REL 2214", "Christian Ethics"),
        ("REL 2217", "Introduction to the Bible"),
        ("REL 2218", "Basic Christian Beliefs"),
        ("SPA 2320", "Introduction to Literature in Spanish"),
        ("ARH 1100", "Survey of Art and Architecture"),
        ("ART 1120", "Design Fundamentals"),
        ("ART 1150", "Principles of Game Design"),
        ("DAN 1600", "Dance Appreciation"),
        ("ENG 2004", "Literary Life"),
        ("MUS 1164", "History of Jazz"),
        ("MUS 1165", "Great Works of Music"),
        ("MUS XXXX - Ensemble", "Ensemble Participation"),
        ("MUS XXXX - Performance", "Music Performance"),
        ("THE 1050", "Introduction to the Theatre"),
        ("THE 1213", "Acting I"),
        ("AST 1010", "Descriptive Astronomy"),
        ("BIO 1005", "Topics in Biology"),
        ("BIO 1500", "Biology I Biological Essentials"),
        ("BIO 2215", "Human Anatomy and Physiology"),
        ("CHE 1005", "Chemistry of Food and Cooking"),
        ("CHE 1050", "Chemical Foundations of Art and Conservation"),
        ("CHE 1111", "Principles of Chemistry I"),
        ("HRT 1000", "Plants and Society"),
        ("HRT 2100", "Intro to Horticultural Science"),
        ("MAT 1007", "Exploring Math in Society & Culture"),
        ("MAT 2022", "Elementary Statistics"),
        ("MAT 2032", "Biostatistics"),
        ("MAT 2311", "Calculus I with Plane Analytic Geometry"),
    ]
]


class ProfileForm(forms.ModelForm):
    """Form for the profile fields a user may edit themselves."""

    about_me = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Maximum 300 words.",
    )
    skills = forms.MultipleChoiceField(
        choices=SKILL_CHOICES,
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
        help_text="Select all skills that apply.",
    )
    classes_taken = forms.MultipleChoiceField(
        choices=COURSE_CHOICES,
        required=False,
        label="Classes Taken",
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Select all completed courses that apply.",
    )
    skills = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="List your skills, one per line or separated by commas.",
    )
    classes_taken = forms.CharField(
        required=False,
        label="Classes Taken",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="List courses you have completed, one per line or separated by commas.",
    )
    interests_clubs = forms.CharField(
        required=False,
        label="Interests & Clubs",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="List your interests or clubs, one per line or separated by commas.",
    )
    timezone = forms.ChoiceField(
        choices=[("", "Select a timezone")] + TIMEZONE_CHOICES,
        required=False,
    )

    class Meta:
        model = Profile
        fields = [
            "avatar",
            "banner_picture",
            "about_me",
            "skills",
            "classes_taken",
            "interests_clubs",
            "timezone",
            "country",
            "city",
            "calling_code",
            "phone_number",
            "github",
            "handshake",
            "yik_yak",
            "linkedin",
            "facebook",
            "discord",
            "instagram",
            "slack",
            "twitter",
        ]
