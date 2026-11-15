from django.db import migrations


def seed_structured_pages(apps, schema_editor):
    PageSettings = apps.get_model("content", "PageSettings")
    SiteSettings = apps.get_model("content", "SiteSettings")
    HomePage = apps.get_model("content", "HomePage")
    HomeFeature = apps.get_model("content", "HomeFeature")
    ImpactStatistic = apps.get_model("content", "ImpactStatistic")
    AboutPage = apps.get_model("content", "AboutPage")
    AboutPillar = apps.get_model("content", "AboutPillar")
    GetInvolvedPage = apps.get_model("content", "GetInvolvedPage")
    InvolvementFeature = apps.get_model("content", "InvolvementFeature")
    DonationOption = apps.get_model("content", "DonationOption")
    InvolvementStep = apps.get_model("content", "InvolvementStep")
    EventsPage = apps.get_model("content", "EventsPage")

    PageSettings.objects.filter(section="news").update(
        hero_heading="News & stories",
        hero_introduction=(
            "What's new at AFS: event recaps, student journeys and the people "
            "who make it happen."
        ),
    )
    PageSettings.objects.filter(section="gallery").update(
        hero_heading="Moments that tell our story.",
        hero_introduction=(
            "Summits, workshops and outreach days across Morocco, captured by "
            "our volunteers and the students themselves."
        ),
    )

    SiteSettings.objects.update_or_create(
        site_key="main",
        defaults={
            "organization_name": "Ask For Success",
            "tagline": "Where your success story begins.",
            "contact_email": "askforsuccess@gmail.com",
            "contact_phone": "+212 6 00 00 00 00",
            "contact_location": "Casablanca, Morocco",
        },
    )

    home, _ = HomePage.objects.update_or_create(
        page_key="home",
        defaults={
            "hero_heading": "Where your success story",
            "hero_highlight": "begins",
            "hero_body": (
                "Empowering Morocco's youth through mentorship, education, "
                "leadership, and community."
            ),
            "primary_cta_label": "Donate",
            "primary_cta_url": "/get-involved/#donate",
            "secondary_cta_label": "Become a partner",
            "secondary_cta_url": "/get-involved/#partner",
            "about_heading": "About Our Association",
            "about_body": (
                "Ask For Success is a Moroccan non-profit dedicated to opening "
                "doors for students and young people. Through events, mentorship, "
                "and community support, we help turn opportunity into real "
                "success stories."
            ),
            "about_cta_label": "Learn More About Us",
            "about_cta_url": "/about/",
            "involvement_heading": "Ways to get involved",
            "involvement_subheading": "Three ways to make an impact.",
            "involvement_body": (
                "Every contribution, whether your time, professional expertise, "
                "or financial patronage, directly enriches a young Moroccan's future."
            ),
            "events_heading": "Upcoming Events",
            "events_subheading": "Meet, learn, and contribute at our next activities.",
        },
    )
    HomeFeature.objects.filter(page=home).delete()
    HomeFeature.objects.bulk_create(
        [
            HomeFeature(
                page=home,
                icon_key="donate",
                title="Donate",
                body=(
                    "Fuel student workshops, equipment, and youth outreach "
                    "programs."
                ),
                cta_label="Learn more",
                cta_url="/get-involved/#donate",
                display_order=1,
            ),
            HomeFeature(
                page=home,
                icon_key="volunteer",
                title="Volunteer",
                body=(
                    "Offer your mentorship or operational time to empower "
                    "Moroccan students."
                ),
                cta_label="Learn more",
                cta_url="/get-involved/#volunteer",
                display_order=2,
            ),
            HomeFeature(
                page=home,
                icon_key="partner",
                title="Partner",
                body=(
                    "Collaborate as an educational institution, NGO, or "
                    "corporate sponsor."
                ),
                cta_label="Learn more",
                cta_url="/get-involved/#partner",
                display_order=3,
            ),
        ]
    )

    ImpactStatistic.objects.all().delete()
    ImpactStatistic.objects.bulk_create(
        [
            ImpactStatistic(value="1,200+", label="Students supported", display_order=1),
            ImpactStatistic(value="40+", label="Events organized", display_order=2),
            ImpactStatistic(value="25+", label="Partners & Sponsors", display_order=3),
            ImpactStatistic(value="300+", label="Active volunteers", display_order=4),
        ]
    )

    about, _ = AboutPage.objects.update_or_create(
        page_key="about",
        defaults={
            "hero_heading": "Opening doors for the",
            "hero_highlight": "next generation.",
            "hero_body": (
                "Ask For Success is a Moroccan non-profit association dedicated "
                "to helping students and young people access the opportunities, "
                "education, and community support they need to succeed."
            ),
            "mission_heading": "Our Mission",
            "mission_subheading": "Turning potential into achievement, together.",
            "mission_body": (
                "Our mission is to bridge the gap between ambition and opportunity. "
                "We work alongside students, volunteers, and partners to create "
                "real pathways through events, mentorship, and community initiatives."
            ),
            "pillars_heading": "What drives us forward",
            "pillars_subheading": "Four pillars, one purpose.",
            "pillars_cta_label": "See how you can help",
            "pillars_cta_url": "/get-involved/",
            "story_heading": "Where it all began",
            "story_subheading": "A small idea that grew into a movement.",
            "story_body": (
                "Ask For Success was founded with a simple belief: success "
                "shouldn't be a privilege reserved for the few. What started as "
                "a small group of students and volunteers has grown into a "
                "community-driven association supporting the next generation."
            ),
            "closing_heading": "Be part of the story",
            "closing_body": (
                "Whether you volunteer your time, support a cause, or partner "
                "with us, you help write the next success story."
            ),
            "primary_cta_label": "Donate",
            "primary_cta_url": "/get-involved/#donate",
            "secondary_cta_label": "Become a partner",
            "secondary_cta_url": "/get-involved/#partner",
        },
    )
    AboutPillar.objects.filter(page=about).delete()
    AboutPillar.objects.bulk_create(
        [
            AboutPillar(
                page=about,
                icon_key="education",
                title="Education",
                body=(
                    "We support learning through mentorship, workshops, and "
                    "knowledge-sharing initiatives."
                ),
                display_order=1,
            ),
            AboutPillar(
                page=about,
                icon_key="opportunity",
                title="Opportunity",
                body=(
                    "We connect students with events, resources, and experiences "
                    "that open doors."
                ),
                display_order=2,
            ),
            AboutPillar(
                page=about,
                icon_key="community",
                title="Community",
                body=(
                    "We build a network of students, volunteers, and partners who "
                    "support each other."
                ),
                display_order=3,
            ),
            AboutPillar(
                page=about,
                icon_key="impact",
                title="Impact",
                body=(
                    "We measure success in the real change created in young "
                    "people's lives."
                ),
                display_order=4,
            ),
        ]
    )

    get_involved, _ = GetInvolvedPage.objects.update_or_create(
        page_key="get_involved",
        defaults={
            "hero_heading": "There's a place for",
            "hero_highlight": "you here.",
            "hero_body": (
                "Every success story needs people behind it. Whether you have "
                "time, resources, or a network to offer, AFS has a way for you to help."
            ),
            "primary_cta_label": "Donate",
            "primary_cta_url": "/get-involved/#donate",
            "secondary_cta_label": "Become a volunteer",
            "secondary_cta_url": "/get-involved/#volunteer",
            "volunteer_heading": "Volunteer with us",
            "volunteer_subheading": "Give a few hours, change a whole year.",
            "volunteer_body": (
                "Volunteers are the heart of every AFS event. Choose how and "
                "when you help: on the ground, online, or one-to-one with a student."
            ),
            "volunteer_cta_label": "Apply to volunteer",
            "volunteer_cta_url": "/opportunities/",
            "partner_heading": "Partner with AFS",
            "partner_subheading": "For schools, companies and NGOs.",
            "partner_body": (
                "Partners open doors we cannot open alone: internships, venues, "
                "equipment and expertise."
            ),
            "partner_cta_label": "Become a partner",
            "partner_cta_url": "/contact/",
            "donation_heading": "Make a donation",
            "donation_subheading": "Every dirham goes to a student programme.",
            "contact_prompt": (
                "Not sure which path is right for you? Contact us and we will help "
                "you find the best way to get involved."
            ),
            "contact_cta_label": "Contact us",
            "contact_cta_url": "/contact/",
            "process_heading": "From sign-up to first event",
            "process_subheading": "Four steps, about two weeks.",
        },
    )
    InvolvementFeature.objects.filter(page=get_involved).delete()
    InvolvementFeature.objects.bulk_create(
        [
            InvolvementFeature(page=get_involved, section="volunteer", title="Event support", body="Welcome students and help events run smoothly.", display_order=1),
            InvolvementFeature(page=get_involved, section="volunteer", title="Mentoring", body="Guide a student's studies or career.", display_order=2),
            InvolvementFeature(page=get_involved, section="volunteer", title="Workshop facilitation", body="Lead a session on a skill you know.", display_order=3),
            InvolvementFeature(page=get_involved, section="volunteer", title="Communication", body="Help tell the story through photos, video, and social media.", display_order=4),
            InvolvementFeature(page=get_involved, section="partner", title="Venues & event sponsorship", display_order=1),
            InvolvementFeature(page=get_involved, section="partner", title="Internships & job shadowing", display_order=2),
            InvolvementFeature(page=get_involved, section="partner", title="Workshops in your field", display_order=3),
            InvolvementFeature(page=get_involved, section="partner", title="Yearly impact report", display_order=4),
        ]
    )
    DonationOption.objects.filter(page=get_involved).delete()
    DonationOption.objects.bulk_create(
        [
            DonationOption(
                page=get_involved,
                title="Give cash",
                instructions=[
                    "Fill in a short form with your details.",
                    "We contact you with the donation instructions.",
                    "You receive a confirmation from AFS.",
                ],
                cta_label="Donate cash",
                cta_url="/contact/?subject=cash-donation",
                display_order=1,
            ),
            DonationOption(
                page=get_involved,
                title="Give goods",
                instructions=[
                    "Tell us what you would like to give.",
                    "We arrange drop-off or pickup for accepted goods.",
                    "You receive a confirmation from AFS.",
                ],
                cta_label="Donate goods",
                cta_url="/contact/?subject=goods-donation",
                display_order=2,
            ),
        ]
    )
    InvolvementStep.objects.filter(page=get_involved).delete()
    InvolvementStep.objects.bulk_create(
        [
            InvolvementStep(page=get_involved, title="Apply online", body="Fill in the short form.", display_order=1),
            InvolvementStep(page=get_involved, title="Meet the team", body="We contact you to understand your skills and availability.", display_order=2),
            InvolvementStep(page=get_involved, title="Get matched", body="We suggest a role, event, or student that fits what you offer.", display_order=3),
            InvolvementStep(page=get_involved, title="Start helping", body="Join your first activity with an experienced member.", display_order=4),
        ]
    )

    EventsPage.objects.update_or_create(
        page_key="events",
        defaults={
            "hero_heading": "Events that",
            "hero_highlight": "open doors",
            "hero_body": (
                "Summits, workshops and outreach days where students meet "
                "mentors, partners, and each other."
            ),
            "hero_cta_label": "See upcoming events",
            "hero_cta_url": "/events/#upcoming",
            "next_heading": "Next event",
            "next_subheading": "Registration is open.",
            "upcoming_heading": "Upcoming events",
            "upcoming_subheading": "Pick one and save your seat.",
            "past_heading": "Past events",
            "past_subheading": "What we've done together so far.",
        },
    )


def remove_structured_pages(apps, schema_editor):
    for model_name in (
        "HomePage",
        "AboutPage",
        "GetInvolvedPage",
        "EventsPage",
        "SiteSettings",
        "ImpactStatistic",
    ):
        apps.get_model("content", model_name).objects.all().delete()
    PageSettings = apps.get_model("content", "PageSettings")
    PageSettings.objects.update(hero_heading="", hero_introduction="")


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0004_pagesettings_hero_heading_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_structured_pages, remove_structured_pages),
    ]
