import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler
import pdb


# Freely copied from the watchdog intro example
# Logs any type of file change to console i.e. terminal
# def log_all(path):
#     logging.basicConfig(level=logging.INFO,
#                         format='%(asctime)s - %(message)s',
#                         datefmt='%Y-%m-%d %H:%M:%S')
#     # path = sys.argv[1] if len(sys.argv) > 1 else './test/'
#     event_handler = LoggingEventHandler()
#     obs = Observer()
#     obs.schedule(event_handler, path, recursive=True)
#     obs.start()
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()


def pump_action():
    print('Trying to pump X ul...')


# Following example at:
# http://brunorocha.org/python/\
# watching-a-directory-for-file-changes-with-python.html
# Making the observer only react to created files
class FileCreatorWatch(PatternMatchingEventHandler):
    def __init__(self, patterns, ignore_directories=True):
        super().__init__()
        self._ignore_directories = ignore_directories
        self._patterns = patterns

    # This class-method will handle the steps taken to pump X ul
    def process_created(self, event):
        """
        event.event_type:
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory:
            True | False
        event.src_path:
            path/to/observed/file
        """
        # pdb.set_trace()
        if event.event_type == 'created':
            # Here add some process that will later represent a pump action
            print('{} was added'.format(event.src_path))
            pump_action()

    # React only to created files
    def on_created(self, event):
        self.process_created(event)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else './test'
    # log_all(path)
    # log_creation(path)
    observer = Observer()
    file_create_handler = FileCreatorWatch(
        patterns=['*.txt'])
    # file_create_handler = FileCreatorWatch()
    observer.schedule(file_create_handler, path)

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print('KeyboardInterrupt caught, stopping process....')
    observer.join()
