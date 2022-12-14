import threading
from socketserver import TCPServer, ThreadingMixIn


class ThreadingTCPListener(ThreadingMixIn, TCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_reuse_address = True


class Server:
    def __init__(self, addresses, handler):
        addresses = [tuple(address) for address in addresses]
        self.servers = [ThreadingTCPListener(address, handler) for address in addresses]
        self._shutdown = threading.Event()

    def serve_forever(self):
        threads = [threading.Thread(target=server.serve_forever) for server in self.servers]
        for thread in threads:
            thread.daemon = True
            thread.start()
        try:
            self._shutdown.wait()
        except KeyboardInterrupt:
            self.shutdown()
        finally:
            for thread in threads:
                thread.join()

    def shutdown(self):
        print('Shutting down')
        for server in self.servers:
            server.shutdown()
        self._shutdown.set()
