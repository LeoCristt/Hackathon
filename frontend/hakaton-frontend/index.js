const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const port = 4000;

app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    next();
});

app.get('/', (req, res) => {
    res.setHeader('Content-Type', 'application/javascript');
    res.sendFile(path.join(__dirname, 'widget.js'));
});

app.get('/html', (req, res) => {
    const htmlContent = fs.readFileSync(path.join(__dirname, 'widget.html'), 'utf8');
    res.json({ html: htmlContent });
});

app.get('/css', (req, res) => {
    const cssContent = fs.readFileSync(path.join(__dirname, 'widget.css'), 'utf8');
    res.json({ css: cssContent });
});

app.listen(port, () => {
    console.log(`Server running at http://172.29.67.31:${port}`);
});
