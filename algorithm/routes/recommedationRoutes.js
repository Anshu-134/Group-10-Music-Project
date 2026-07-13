import express from "express";
import { getRecommendations } from "../algorithm/src/services/recommendationService.js";

const router = express.Router();

router.get("/recommendations/:userId", async (req, res) => {
  const data = await getRecommendations(req.params.userId);
  res.json(data);
});

export default router;