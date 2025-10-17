const express = require('express');
const path = require('path');
const app = express();
const port = 3300;

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'demo.html'));
});

app.get('/manager', (req, res) => {
    res.sendFile(path.join(__dirname, 'manager.html'));
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
    console.log(`Demo page: http://localhost:${port}`);
    console.log(`Manager panel: http://localhost:${port}/manager`);
});
