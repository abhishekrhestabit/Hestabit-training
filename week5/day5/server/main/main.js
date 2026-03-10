const express = require('express');
const mongoose = require('mongoose');
const router = express.Router();

// SCHEMA
const goalSchema = new mongoose.Schema({
  title: { type: String, required: true },
  deadline: { type: String },
  status: { type: String, default: 'pending' },
}, { timestamps: true });

const Goal = mongoose.model('Goal', goalSchema);

// API ROUTES

router.get('/', async (req, res) => {
  try {
    const goals = await Goal.find({}).sort({ createdAt: -1 });
    res.json(goals);
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});


router.post('/', async (req, res) => {
  try {
    const { title, deadline } = req.body;
    
    const goal = await Goal.create({
      title,
      deadline
    });

    res.status(201).json(goal);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});


router.put('/:id', async (req, res) => {
  try {
    const goal = await Goal.findByIdAndUpdate(
      req.params.id, 
      req.body,
      { new: true }
    );
    
    res.json(goal);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

router.delete('/:id', async (req, res) => {
  try {
    const goal = await Goal.findByIdAndDelete(req.params.id);
    
    if (!goal) {
      return res.status(404).json({ message: 'Todo not found' });
    }

    res.json({ message: 'Todo deleted successfully' });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;