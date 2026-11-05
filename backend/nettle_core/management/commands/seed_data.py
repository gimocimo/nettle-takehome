from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessments.models import Assessment
from evidence.models import Evidence
from portfolio.models import Client
from tenancy.models import Membership, Organization

# Development-only credentials, documented in the README. Never used outside DEBUG.
DEMO_PASSWORD = "nettle-demo-2026"

ORGANIZATIONS = [
    # slug, name, language, currency
    ("default-insurer", "Default Insurer", "en-GB", "GBP"),
    ("customer-a", "Customer A", "en-GB", "EUR"),
    ("customer-b", "Customer B", "en-GB", "GBP"),
]

USERS = [
    # email, first name, {organization slug: role}
    ("admin@default.test", "Dana", {"default-insurer": Membership.ADMIN}),
    ("engineer@default.test", "Eli", {"default-insurer": Membership.ENGINEER}),
    ("viewer@default.test", "Vic", {"default-insurer": Membership.VIEWER}),
    ("admin@customer-a.test", "Ada", {"customer-a": Membership.ADMIN}),
    ("admin@customer-b.test", "Ben", {"customer-b": Membership.ADMIN}),
    (
        "consultant@nettle.test",
        "Cora",
        {
            "default-insurer": Membership.ENGINEER,
            "customer-a": Membership.VIEWER,
            "customer-b": Membership.ENGINEER,
        },
    ),
]


class Command(BaseCommand):
    help = "Seed demo organizations, users and data (development only)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="Seed even when DJANGO_DEBUG is off.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError(
                "Refusing to seed demo data with DJANGO_DEBUG off "
                "(pass --allow-production to override)."
            )
        if Organization.objects.filter(slug__in=[org[0] for org in ORGANIZATIONS]).exists():
            self.stdout.write("Demo data already exists, skipping seed.")
            return

        # All or nothing: a failure halfway must not leave a partial seed behind,
        # because the "already exists" check above would then skip it forever.
        # Runs without a tenant context: seeding is a privileged, cross-tenant operation.
        with transaction.atomic():
            orgs = self._seed_organizations_and_users()
            self._seed_default_insurer(orgs["default-insurer"])
            self._seed_customer_a(orgs["customer-a"])
            self._seed_customer_b(orgs["customer-b"])
        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    def _seed_organizations_and_users(self):
        orgs = {
            slug: Organization.objects.create(slug=slug, name=name, language=language, currency=currency)
            for slug, name, language, currency in ORGANIZATIONS
        }
        User = get_user_model()
        for email, first_name, roles in USERS:
            user = User.objects.create_user(
                username=email, email=email, password=DEMO_PASSWORD, first_name=first_name
            )
            for slug, role in roles.items():
                Membership.objects.create(user=user, organization=orgs[slug], role=role)
        # Nettle staff: Django admin only, no tenant memberships.
        User.objects.create_superuser(
            username="staff@nettle.test", email="staff@nettle.test", password=DEMO_PASSWORD
        )
        return orgs

    def _seed_default_insurer(self, organization):
        client1 = Client.objects.create(
            organization=organization,
            name="Hartfield Manufacturing Ltd",
            contact_name="James Whitaker",
            contact_email="j.whitaker@hartfield.co.uk",
            contact_phone="+44 20 7946 0123",
            industry="Manufacturing",
            sub_industry="Metal Fabrication",
            company_size="large",
            annual_revenue=45000000.00,
            employee_count=380,
            year_established=1987,
            address_line_1="Unit 4, Riverside Industrial Estate",
            city="Sheffield",
            state_province="South Yorkshire",
            postal_code="S9 2PQ",
            country="United Kingdom",
            policy_number="HM-2024-00891",
            broker_name="Marsh McLennan",
            broker_contact="Sarah Patel",
            coverage_type="Commercial Property",
            total_insured_value=28000000.00,
            risk_rating="medium",
            previous_claims_count=2,
            notes="Major renovation of Building B completed 2023. New fire suppression system installed.",
        )

        client2 = Client.objects.create(
            organization=organization,
            name="Pacific Coast Logistics",
            contact_name="Maria Chen",
            contact_email="m.chen@paccoast.com",
            contact_phone="+1 310 555 0147",
            industry="Logistics",
            sub_industry="Warehousing & Distribution",
            company_size="enterprise",
            annual_revenue=120000000.00,
            employee_count=1200,
            year_established=2001,
            address_line_1="8500 Port Boulevard",
            city="Long Beach",
            state_province="California",
            postal_code="90802",
            country="United States",
            policy_number="PCL-2024-03421",
            broker_name="Aon",
            broker_contact="David Kim",
            coverage_type="Commercial Property & Cargo",
            total_insured_value=95000000.00,
            risk_rating="high",
            previous_claims_count=5,
            notes="Multiple warehouse locations. High-value cargo storage. Previous water damage claims.",
        )

        Client.objects.create(
            organization=organization,
            name="Greenfield Retail Group",
            contact_name="Tom Bradley",
            contact_email="t.bradley@greenfield.com",
            contact_phone="+44 161 496 0234",
            industry="Retail",
            sub_industry="Shopping Centres",
            company_size="enterprise",
            annual_revenue=200000000.00,
            employee_count=3500,
            year_established=1995,
            address_line_1="Greenfield House, 120 Deansgate",
            city="Manchester",
            state_province="Greater Manchester",
            postal_code="M3 2GP",
            country="United Kingdom",
            coverage_type="Commercial Property",
            total_insured_value=450000000.00,
            risk_rating="medium",
            previous_claims_count=1,
        )

        assessment1 = Assessment.objects.create(
            title="Annual Property Inspection - Hartfield Sheffield",
            client=client1,
            status="in_progress",
            site_address="Unit 4, Riverside Industrial Estate, Sheffield S9 2PQ",
            assessor_name="David Morgan",
            assessment_date=date(2024, 11, 15),
            notes="Focus on new fire suppression system and Building B renovation.",
        )

        assessment2 = Assessment.objects.create(
            title="Q4 Warehouse Risk Review - Pacific Coast",
            client=client2,
            status="in_progress",
            site_address="8500 Port Boulevard, Long Beach, CA 90802",
            assessor_name="Rachel Torres",
            assessment_date=date(2024, 11, 20),
        )

        self._note(assessment1, "General site condition", "The manufacturing facility is well-maintained overall. Main production floor is clean and organised. Emergency exits clearly marked and unobstructed. Staff wearing appropriate PPE throughout observed areas.")
        self._note(assessment1, "Fire suppression system", "New wet sprinkler system installed in Building B during 2023 renovation. System is FM Global approved. Last tested October 2024 — all heads functional. Pump room is clean, well-lit, and accessible. Fire alarm panel in reception shows no faults. However, noted that sprinkler heads in the paint storage area (Room B-14) appear to be standard response rather than quick response as required for this occupancy type.")
        self._note(assessment1, "Electrical observations", "Main electrical panel in good condition, last inspected March 2024. Thermal imaging scan conducted — no hotspots detected. However, several extension leads observed in the packaging area running across walkways, creating trip hazard and potential electrical risk. One junction box in the loading bay has a missing cover plate.")
        self._note(assessment1, "Structural observations", "Building A (original 1987 construction) shows some age-related wear. Roof membrane has minor ponding in northwest corner — maintenance team aware and monitoring. Building B (2023 renovation) is in excellent condition. Steel frame, composite cladding, rated for intended use. Loading bay roller shutters operational, one showing slight misalignment.")
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="document",
            title="Fire system test certificate",
            text_content="Certificate of Compliance - Wet Sprinkler System. Building B, Hartfield Manufacturing. System tested 15 October 2024. All zones operational. Flow test satisfactory. Next test due: April 2025. Issued by: FireSafe Inspections Ltd.",
        )

        self._note(assessment2, "Warehouse A - General", "250,000 sq ft warehouse, racked storage to 40ft. Sprinkler system present but showing signs of corrosion on branch lines in the south section. Housekeeping is poor — cardboard and shrink wrap debris accumulated near loading docks.")
        self._note(assessment2, "High-value cargo storage", "Separate secure area for high-value electronics storage. Access controlled, CCTV monitored. Temperature and humidity controlled. However, the backup generator for this area was last tested 8 months ago (quarterly testing recommended). No water leak detection sensors installed despite previous water damage claims.")
        self._add_files(
            assessment2,
            [
                ("Rack_storage_Open_Shelf_1_11.jpg", "Warehouse A - open shelf racking"),
                ("In_Rack_face_sprinkler_3.jpg", "Warehouse A - in-rack sprinkler"),
                ("Storage_Containment_for_flammable_liquid_IBCs_4.jpg", "Flammable liquid IBC containment"),
            ],
        )

    def _seed_customer_a(self, organization):
        client = Client.objects.create(
            organization=organization,
            name="Hazardous Goods Warehousing Service GmbH",
            contact_name="Site manager",
            contact_email="site@hgws.example",
            industry="Logistics",
            sub_industry="Hazardous goods storage",
            company_size="medium",
            annual_revenue=18000000.00,
            employee_count=140,
            year_established=2009,
            address_line_1="Via Ivan Trinko, 11",
            city="Udine",
            state_province="UD",
            postal_code="33100",
            country="Italy",
            coverage_type="Property",
        )
        assessment = Assessment.objects.create(
            title="Hazardous goods warehouse survey - Udine",
            client=client,
            status="in_progress",
            site_address="Via Ivan Trinko, 11, 33100 Udine UD, Italy",
            assessor_name="Peter Eymael",
            assessment_date=date(2025, 3, 12),
        )
        self._add_files(
            assessment,
            [
                ("Hazardous_Goods_Warehouse_Description_12.pdf", "Warehouse description and risk improvement advice"),
                ("Rack_Storage_Open_Shelf_IRAS_3_6.jpg", "High-bay rack storage with in-rack sprinklers"),
                ("Solid_piled_storage_1_2.jpg", "Inbound buffer: solid piled storage"),
                ("Flow_through_racks_8.jpg", "Picking area: flow-through racks"),
            ],
        )

    def _seed_customer_b(self, organization):
        client = Client.objects.create(
            organization=organization,
            name="Leeds Distribution Centre",
            contact_name="Facilities team",
            contact_email="facilities@leeds-dc.example",
            industry="Retail",
            sub_industry="Distribution centre",
            company_size="large",
            annual_revenue=60000000.00,
            employee_count=420,
            year_established=2012,
            address_line_1="Stourton Link",
            city="Leeds",
            state_province="West Yorkshire",
            postal_code="LS10 1AA",
            country="United Kingdom",
            coverage_type="Self-insured",
        )
        assessment = Assessment.objects.create(
            title="Forklift charging and storage safety review",
            client=client,
            status="in_progress",
            site_address="Stourton Link, Leeds LS10 1AA",
            assessor_name="Internal H&S team",
            assessment_date=date(2026, 10, 2),
        )
        self._note(assessment, "Charging area", "Forklift charging bays are next to stored cardboard packaging. No separation distance marked on the floor. Charging area ventilation not verified during the visit.")
        self._add_files(
            assessment,
            [
                ("Fork_lift_charging_1_5.jpg", "Forklift charging bay 1"),
                ("Fork_lift_charging_2.jpg", "Forklift charging bay 2"),
                ("Fire extinguishers.jpg", "Extinguisher point near the charging area"),
            ],
        )

    def _note(self, assessment, title, text):
        Evidence.objects.create(assessment=assessment, evidence_type="note", title=title, text_content=text)

    def _add_files(self, assessment, files):
        """Attach sample photos and documents, if the sample_evidence folder is mounted."""
        source_dir = Path("/app/sample_evidence")
        if not source_dir.is_dir():
            source_dir = Path(__file__).resolve().parents[4] / "sample_evidence"
        if not source_dir.is_dir():
            self.stdout.write("sample_evidence not found, skipping files.")
            return

        for filename, title in files:
            path = source_dir / filename
            if not path.is_file():
                continue
            is_pdf = path.suffix.lower() == ".pdf"
            item = Evidence(
                assessment=assessment,
                evidence_type="document" if is_pdf else "image",
                media_type="application/pdf" if is_pdf else "image/jpeg",
                original_filename=filename,
                title=title,
            )
            with path.open("rb") as fh:
                item.file.save(filename, File(fh), save=True)
