import signal

from django.core.management.base import BaseCommand

from modules.data_import.infrastructure.worker import process_next, run_forever


class Command(BaseCommand):
    help = 'Ejecuta en segundo plano las importaciones de ventas en cola. Con --once procesa la cola y termina.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Procesa las corridas en cola y termina.')
        parser.add_argument('--poll', type=float, default=2.0, help='Segundos entre consultas de la cola.')

    def handle(self, *args, **options):
        if options['once']:
            processed = 0
            while process_next():
                processed += 1
            self.stdout.write(f'Importaciones procesadas: {processed}')
            return
        stopping = {'value': False}

        def stop(*_):
            stopping['value'] = True  # termina la corrida en curso y sale

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        self.stdout.write('Worker de importaciones iniciado.')
        run_forever(options['poll'], lambda: stopping['value'])
