from django.core.management.base import BaseCommand
from payments.services import PaymentService

class Command(BaseCommand):
    help = 'Check and update status of idle payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=30,
            help='Number of minutes to consider a payment as idle'
        )

    def handle(self, *args, **options):
        idle_minutes = options['minutes']
        self.stdout.write(f'Checking payments idle for {idle_minutes} minutes...')
        
        PaymentService.handle_idle_payments(idle_minutes)
        
        self.stdout.write(self.style.SUCCESS('Successfully processed idle payments')) 