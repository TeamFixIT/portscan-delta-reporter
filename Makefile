.PHONY: server-run server-test server-format client-run

server-run:
\tcd server && FLASK_ENV=development portscanner-server

server-test:
\tcd server && pytest

server-format:
\tcd server && black app tests

client-run:
\tcd client && python3 client_agent.py
