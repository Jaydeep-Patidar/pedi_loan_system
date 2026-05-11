"""
Fake/Test Seed Data Generator

This command generates fake demo data
for development and testing purposes only.
"""


# core/management/commands/seed_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum

from faker import Faker
from random import choice, randint, random
from decimal import Decimal
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from core.models import (
    Member,
    Pedi,
    MemberPedi,
    Payment,
    Loan,
    LoanPayment,
    Transaction,
    LoanTransaction,
    LoanApplication,
    LoanApplicationSettings,
    Notice
)

fake = Faker()


class Command(BaseCommand):

    help = "Generate fake seed data"

    def add_arguments(self, parser):

        parser.add_argument(
            '--users',
            type=int,
            default=25
        )

    @transaction.atomic
    def handle(self, *args, **options):

        total_users = options['users']

        self.stdout.write(
            self.style.WARNING(
                "Deleting old data..."
            )
        )

        # -----------------------------------
        # DELETE OLD DATA
        # -----------------------------------
        LoanTransaction.objects.all().delete()
        LoanPayment.objects.all().delete()
        Transaction.objects.all().delete()
        Payment.objects.all().delete()
        LoanApplication.objects.all().delete()
        Loan.objects.all().delete()
        MemberPedi.objects.all().delete()
        Notice.objects.all().delete()
        LoanApplicationSettings.objects.all().delete()
        Pedi.objects.all().delete()
        Member.objects.all().delete()

        User.objects.filter(
            is_superuser=False
        ).delete()

        # -----------------------------------
        # CREATE ADMIN
        # -----------------------------------
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@test.com',
                'is_superuser': True,
                'is_staff': True
            }
        )

        admin_user.set_password('Admin@123')
        admin_user.save()

        Member.objects.get_or_create(
            user=admin_user,
            defaults={
                'email': admin_user.email,
                'phone': '9999999999',
                'address': 'Admin Office',
                'role': 'admin',
                'is_active': True
            }
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Admin created"
            )
        )

        # -----------------------------------
        # CREATE LOAN SETTINGS
        # -----------------------------------
        loan_settings = LoanApplicationSettings.objects.create(

            start_date=timezone.now().date() - timedelta(days=10),

            end_date=timezone.now().date() + timedelta(days=365),

            default_interest_rate=Decimal('10.00'),

            default_loan_duration_months=12,

            penalty_enabled=True,

            grace_days=5,

            enable_late_fee_per_day=True,

            late_fee_per_day=Decimal('20.00'),

            enable_fixed_penalty=True,

            fixed_penalty_amount=Decimal('100.00'),

            enable_percentage_penalty=True,

            percentage_penalty_rate=Decimal('2.00')
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Loan settings created"
            )
        )

        # -----------------------------------
        # CREATE PEDI PLANS
        # -----------------------------------
        pedi_list = []

        for i in range(5):

            penalty_enabled = choice([
                True,
                False
            ])

            pedi = Pedi.objects.create(

                name=f"Pedi Plan {i+1}",

                duration_months=choice([
                    6,
                    12,
                    18
                ]),

                monthly_amount=Decimal(
                    randint(500, 5000)
                ),

                start_date=timezone.now().date(),

                is_active=True,

                penalty_enabled=penalty_enabled,

                grace_days=3 if penalty_enabled else 0,

                enable_late_fee_per_day=penalty_enabled,

                late_fee_per_day=(
                    Decimal('20.00')
                    if penalty_enabled
                    else Decimal('0.00')
                ),

                enable_fixed_penalty=penalty_enabled,

                fixed_penalty_amount=(
                    Decimal('100.00')
                    if penalty_enabled
                    else Decimal('0.00')
                ),

                enable_percentage_penalty=penalty_enabled,

                percentage_penalty_rate=(
                    Decimal('2.00')
                    if penalty_enabled
                    else Decimal('0.00')
                )
            )

            pedi_list.append(pedi)

        self.stdout.write(
            self.style.SUCCESS(
                "Pedi plans created"
            )
        )

        # -----------------------------------
        # CREATE MEMBERS
        # -----------------------------------
        for i in range(total_users):

            first_name = fake.first_name()
            last_name = fake.last_name()

            user = User.objects.create_user(

                username=fake.unique.user_name(),

                first_name=first_name,

                last_name=last_name,

                email=fake.unique.email(),

                password='Test@123'
            )

            member = Member.objects.create(

                user=user,

                email=user.email,

                phone=f"9{randint(100000000, 999999999)}",

                address=fake.address(),

                role='member',

                is_active=choice([
                    True,
                    True,
                    True,
                    False
                ])
            )

            # -----------------------------------
            # ASSIGN PEDI
            # -----------------------------------
            selected_pedis = fake.random_elements(
                elements=pedi_list,
                length=randint(1, 2),
                unique=True
            )

            for pedi in selected_pedis:

                MemberPedi.objects.create(

                    member=member,

                    pedi=pedi,

                    status=choice([
                        'Active',
                        'Completed',
                        'Defaulted'
                    ])
                )

                # -----------------------------------
                # CREATE PAYMENTS
                # -----------------------------------
                for i in range(pedi.duration_months):

                    payment_date_obj = (
                        pedi.start_date +
                        relativedelta(months=i)
                    )

                    payment_month = payment_date_obj.month
                    payment_year = payment_date_obj.year

                    payment_status = choice([
                        'Paid',
                        'Pending'
                    ])

                    if payment_status == 'Paid':

                        payment_date = (
                            timezone.now() -
                            timedelta(days=randint(1, 150))
                        )

                        payment_method = choice([
                            'Cash',
                            'Online'
                        ])

                    else:

                        payment_date = None
                        payment_method = 'Cash'

                    transaction_id = None

                    if payment_status == 'Paid':

                        transaction_id = (
                            f"PMT-{timezone.now().strftime('%Y%m%d%H%M%S')}-{randint(1000,9999)}"
                        )

                    razorpay_order_id = None
                    razorpay_payment_id = None

                    if payment_method == 'Online':

                        razorpay_order_id = (
                            f"order_{fake.lexify(text='??????????')}"
                        )

                        razorpay_payment_id = (
                            f"pay_{fake.lexify(text='??????????')}"
                        )

                    payment = Payment.objects.create(

                        member=member,

                        pedi=pedi,

                        month=payment_month,

                        year=payment_year,

                        amount=pedi.monthly_amount,

                        status=payment_status,

                        payment_date=payment_date,

                        payment_method=payment_method,

                        transaction_id=transaction_id,

                        razorpay_order_id=razorpay_order_id,

                        razorpay_payment_id=razorpay_payment_id,

                        penalty_enabled=pedi.penalty_enabled,

                        grace_days=pedi.grace_days,

                        enable_late_fee_per_day=pedi.enable_late_fee_per_day,

                        late_fee_per_day=pedi.late_fee_per_day,

                        enable_fixed_penalty=pedi.enable_fixed_penalty,

                        fixed_penalty_amount=pedi.fixed_penalty_amount,

                        enable_percentage_penalty=pedi.enable_percentage_penalty,

                        percentage_penalty_rate=pedi.percentage_penalty_rate
                    )

                    # -----------------------------------
                    # CREATE TRANSACTION
                    # -----------------------------------
                    if payment_status == 'Paid':

                        txn_status = 'Success'

                    else:

                        txn_status = choice([
                            'Created',
                            'Failed'
                        ])

                    Transaction.objects.create(

                        member=member,

                        payment=payment,

                        razorpay_order_id=(
                            razorpay_order_id or
                            f"order_{fake.lexify(text='??????????')}"
                        ),

                        razorpay_payment_id=(
                            razorpay_payment_id
                        ),

                        razorpay_signature=(
                            fake.sha1()
                            if txn_status == 'Success'
                            else None
                        ),

                        amount=payment.amount,

                        status=txn_status
                    )

            # -----------------------------------
            # LOAN APPLICATION
            # -----------------------------------
            if random() > 0.4:

                application_status = choice([
                    'Pending',
                    'Approved',
                    'Rejected'
                ])

                requested_amount = Decimal(
                    randint(5000, 100000)
                )

                application = LoanApplication.objects.create(

                    member=member,

                    requested_amount=requested_amount,

                    purpose=fake.sentence(),

                    status=application_status,

                    admin_remarks=fake.sentence()
                )

                # -----------------------------------
                # CREATE LOAN
                # -----------------------------------
                if application_status == 'Approved':

                    due_date = (
                        timezone.now().date() +
                        relativedelta(
                            months=loan_settings.default_loan_duration_months
                        )
                    )

                    loan = Loan.objects.create(

                        member=member,

                        amount=requested_amount,

                        interest_rate=loan_settings.default_interest_rate,

                        due_date=due_date,

                        penalty_enabled=loan_settings.penalty_enabled,

                        grace_days=loan_settings.grace_days,

                        enable_late_fee_per_day=loan_settings.enable_late_fee_per_day,

                        late_fee_per_day=loan_settings.late_fee_per_day,

                        enable_fixed_penalty=loan_settings.enable_fixed_penalty,

                        fixed_penalty_amount=loan_settings.fixed_penalty_amount,

                        enable_percentage_penalty=loan_settings.enable_percentage_penalty,

                        percentage_penalty_rate=loan_settings.percentage_penalty_rate,

                        status='Active'
                    )

                    application.loan = loan

                    application.approved_date = timezone.now()

                    application.approved_interest_rate = (
                        loan_settings.default_interest_rate
                    )

                    application.approved_due_date = due_date

                    application.save()

                    # -----------------------------------
                    # LOAN PAYMENTS
                    # -----------------------------------
                    payment_count = randint(1, 5)

                    for j in range(payment_count):

                        loan.refresh_from_db()

                        if loan.remaining_due <= 0:
                            break

                        max_amount = int(
                            loan.remaining_due * Decimal('0.40')
                        )

                        if max_amount <= 1000:
                            break

                        payment_amount = Decimal(
                            randint(1000, max_amount)
                        )

                        payment_method = choice([
                            'Cash',
                            'Online'
                        ])

                        loan_payment = LoanPayment.objects.create(

                            loan=loan,

                            amount=payment_amount,

                            transaction_id=(
                                f"LOAN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{randint(1000,9999)}"
                            ),

                            payment_method=payment_method
                        )

                        LoanTransaction.objects.create(

                            loan=loan,

                            amount=loan_payment.amount,

                            razorpay_order_id=(
                                f"order_{fake.lexify(text='??????????')}"
                            ),

                            razorpay_payment_id=(
                                f"pay_{fake.lexify(text='??????????')}"
                            ),

                            razorpay_signature=fake.sha1(),

                            status=choice([
                                'Success',
                                'Created'
                            ])
                        )

        self.stdout.write(
            self.style.SUCCESS(
                "Members, payments and loans created"
            )
        )

        # -----------------------------------
        # CREATE NOTICES
        # -----------------------------------
        for i in range(10):

            Notice.objects.create(

                title=fake.sentence(nb_words=5),

                content=fake.text(max_nb_chars=300),

                author=admin_user,

                is_active=choice([
                    True,
                    True,
                    False
                ])
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Notices created"
            )
        )

        # -----------------------------------
        # SUMMARY
        # -----------------------------------
        total_members = Member.objects.filter(
            role='member'
        ).count()

        total_collection = (
            Payment.objects.filter(
                status='Paid'
            ).aggregate(
                total=Sum('amount')
            )['total']
            or Decimal('0.00')
        )

        total_loan_collection = (
            LoanPayment.objects.aggregate(
                total=Sum('amount')
            )['total']
            or Decimal('0.00')
        )

        total_active_loans = Loan.objects.filter(
            status='Active'
        ).count()

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "========== SUMMARY =========="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Members: {total_members}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Pedi Collection: ₹{total_collection}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Loan Collection: ₹{total_loan_collection}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Active Loans: {total_active_loans}"
            )
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Fake seed data generated successfully"
            )
        )