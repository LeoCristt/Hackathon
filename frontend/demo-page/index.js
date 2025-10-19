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
    console.log(`Server running at http://172.29.67.31:${port}`);
    console.log(`Demo page: http://172.29.67.31t:${port}`);
    console.log(`Manager panel: http://172.29.67.31:${port}/manager`);
});
