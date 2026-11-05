from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from portfolio.models import Client
from assessments.models import Assessment
from evidence.models import Evidence
from reports.models import Report
from datetime import date


class Command(BaseCommand):
    help = "Seed the database with sample data"

    def handle(self, *args, **options):
        if Client.objects.exists():
            self.stdout.write("Data already exists, skipping seed.")
            return

        # Create clients
        client1 = Client.objects.create(
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

        client3 = Client.objects.create(
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

        # Create assessments
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

        # Create evidence for assessment 1
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="note",
            title="General site condition",
            text_content="The manufacturing facility is well-maintained overall. Main production floor is clean and organised. Emergency exits clearly marked and unobstructed. Staff wearing appropriate PPE throughout observed areas.",
        )
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="note",
            title="Fire suppression system",
            text_content="New wet sprinkler system installed in Building B during 2023 renovation. System is FM Global approved. Last tested October 2024 — all heads functional. Pump room is clean, well-lit, and accessible. Fire alarm panel in reception shows no faults. However, noted that sprinkler heads in the paint storage area (Room B-14) appear to be standard response rather than quick response as required for this occupancy type.",
        )
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="note",
            title="Electrical observations",
            text_content="Main electrical panel in good condition, last inspected March 2024. Thermal imaging scan conducted — no hotspots detected. However, several extension leads observed in the packaging area running across walkways, creating trip hazard and potential electrical risk. One junction box in the loading bay has a missing cover plate.",
        )
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="note",
            title="Structural observations",
            text_content="Building A (original 1987 construction) shows some age-related wear. Roof membrane has minor ponding in northwest corner — maintenance team aware and monitoring. Building B (2023 renovation) is in excellent condition. Steel frame, composite cladding, rated for intended use. Loading bay roller shutters operational, one showing slight misalignment.",
        )
        Evidence.objects.create(
            assessment=assessment1,
            evidence_type="document",
            title="Fire system test certificate",
            text_content="Certificate of Compliance - Wet Sprinkler System. Building B, Hartfield Manufacturing. System tested 15 October 2024. All zones operational. Flow test satisfactory. Next test due: April 2025. Issued by: FireSafe Inspections Ltd.",
        )

        # Create evidence for assessment 2
        Evidence.objects.create(
            assessment=assessment2,
            evidence_type="note",
            title="Warehouse A - General",
            text_content="250,000 sq ft warehouse, racked storage to 40ft. Sprinkler system present but showing signs of corrosion on branch lines in the south section. Housekeeping is poor — cardboard and shrink wrap debris accumulated near loading docks.",
        )
        Evidence.objects.create(
            assessment=assessment2,
            evidence_type="note",
            title="High-value cargo storage",
            text_content="Separate secure area for high-value electronics storage. Access controlled, CCTV monitored. Temperature and humidity controlled. However, the backup generator for this area was last tested 8 months ago (quarterly testing recommended). No water leak detection sensors installed despite previous water damage claims.",
        )

        # Site photos taken during the Pacific Coast walkaround
        self._add_photos(
            assessment2,
            [
                ("Rack_storage_Open_Shelf_1_11.jpg", "Warehouse A - open shelf racking"),
                ("In_Rack_face_sprinkler_3.jpg", "Warehouse A - in-rack sprinkler"),
                (
                    "Storage_Containment_for_flammable_liquid_IBCs_4.jpg",
                    "Flammable liquid IBC containment",
                ),
            ],
        )

        # Create a sample report
        Report.objects.create(
            assessment=assessment1,
            title="Risk Report - Hartfield Manufacturing Ltd",
            content="",
            status="pending",
        )

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    def _add_photos(self, assessment, photos):
        """Attach sample site photos, if the sample_evidence folder is mounted."""
        source_dir = Path("/app/sample_evidence")
        if not source_dir.is_dir():
            source_dir = Path(__file__).resolve().parents[4] / "sample_evidence"
        if not source_dir.is_dir():
            self.stdout.write("sample_evidence not found, skipping photos.")
            return

        for filename, title in photos:
            path = source_dir / filename
            if not path.is_file():
                continue
            item = Evidence(
                assessment=assessment,
                evidence_type="image",
                title=title,
            )
            with path.open("rb") as fh:
                item.file.save(filename, File(fh), save=True)
