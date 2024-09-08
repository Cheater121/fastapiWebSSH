document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById('connect');
    const terminalContainer = document.getElementById('terminal');
    const terminal = new Terminal();
    const fitAddon = new FitAddon.FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(terminalContainer);
    fitAddon.fit();

    let socket;

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const hostname = document.getElementById('hostname').value;
        const port = document.getElementById('port').value || 22;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // Establish WebSocket connection
        socket = new WebSocket(`ws://${window.location.host}/ws`);

        socket.onopen = () => {
            terminal.write('Connecting...\r\n');
            // Send connection details to the server
            socket.send(JSON.stringify({ hostname, port, username, password }));
        };

        socket.onmessage = (event) => {
            console.log("Received message:", event.data); // Log received messages
            terminal.write(event.data);
        };

        socket.onclose = () => {
            terminal.write('\r\nConnection closed.\r\n');
        };

        terminal.onData(data => {
            console.log("Sending data:", data); // Log data sent
            // Send the data to the WebSocket
            socket.send(data);
        });

        terminal.onResize(size => {
            console.log("Terminal resized:", size); // Log terminal resize events
            // Notify the server about the terminal resize
            socket.send(JSON.stringify({ type: 'resize', cols: size.cols, rows: size.rows }));
        });
    });

    // Handle WebSocket errors
    socket.onerror = (error) => {
        terminal.write(`\r\nWebSocket error: ${error.message}\r\n`);
    };
});
