/**
 * index.js is the entry point for the algorithm service. Run standalone w/ 'npm start'
 * It is a separate process from the Flask backend, which calls it over HTTP. 
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const recommendationRoutes = require('../routes/recommedationRoutes');
 
const app = express();
app.use(cors());
app.use(express.json());
app.use('/', recommendationRoutes);
 
const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`Algorithm service listening on port ${PORT}`);
});
 
module.exports = app;