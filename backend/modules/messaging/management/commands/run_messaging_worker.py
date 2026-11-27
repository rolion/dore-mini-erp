import signal

from django.core.management.base import BaseCommand

from modules.messaging.infrastructure.worker import process_all, run_forever


class Command(BaseCommand):
    help = 'Procesa los webhooks de WhatsApp y entrega los mensajes en cola. Con --once procesa y termina.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Procesa lo pendiente y termina.')
        parser.add_argument('--poll', type=float, default=2.0, help='Segundos entre consultas de la cola.')

    def handle(self, *args, **options):
        if options['once']:
            self.stdout.write(f'Elementos procesados: {process_all()}')
            return
        stopping = {'value': False}

        def stop(*_):
            stopping['value'] = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        self.stdout.write('Worker de mensajería iniciado.')
        run_forever(options['poll'], lambda: stopping['value'])
