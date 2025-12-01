"""Quest RAG Service"""

import logging
from typing import Dict, List, Optional
from services.db import get_db
from services.embedding import generate_text_embedding
from services.pinecone_store import search_text_embeddings, upsert_text_embedding

logger = logging.getLogger(__name__)


def generate_quest_rag_text(quest: Dict, place: Optional[Dict] = None) -> str:
    parts = []
    
    quest_name = quest.get("name") or quest.get("title", "")
    if quest_name:
        parts.append(f"[Quest] {quest_name}")
    
    quest_description = quest.get("description", "")
    if quest_description:
        parts.append(f"Description: {quest_description}")
    
    quest_category = quest.get("category", "")
    if quest_category:
        parts.append(f"Category: {quest_category}")
    
    quest_difficulty = quest.get("difficulty", "")
    if quest_difficulty:
        parts.append(f"Difficulty: {quest_difficulty}")
    
    parts.append("")
    
    if place:
        place_name = place.get("name", "")
        if place_name:
            parts.append(f"[Place] {place_name}")
        
        place_address = place.get("address", "")
        if place_address:
            parts.append(f"Address: {place_address}")
        
        place_category = place.get("category", "")
        if place_category:
            parts.append(f"Place Category: {place_category}")
        
        place_description = place.get("description", "")
        if place_description:
            parts.append(f"Place Description: {place_description[:300]}...")
        
        place_metadata = place.get("metadata", {})
        if isinstance(place_metadata, dict):
            place_rag_text = place_metadata.get("rag_text", "")
            if place_rag_text:
                parts.append("")
                parts.append("[Place Details]")
                parts.append(place_rag_text[:500])
        
        parts.append("")
    
    quest_id = quest.get("id")
    if quest_id:
        try:
            db = get_db()
            quizzes_result = db.table("quest_quizzes") \
                .select("question, options, explanation") \
                .eq("quest_id", quest_id) \
                .limit(3) \
                .execute()
            
            if quizzes_result.data:
                parts.append("[Quiz Topics]")
                for quiz in quizzes_result.data[:3]:
                    question = quiz.get("question", "")
                    if question:
                        parts.append(f"- {question[:100]}")
                parts.append("")
        except Exception as e:
            logger.warning(f"Failed to fetch quizzes for quest {quest_id}: {e}")
    
    rag_text = "\n".join(parts)
    
    max_length = 2000
    if len(rag_text) > max_length:
        rag_text = rag_text[:max_length] + "..."
        logger.warning(f"Quest RAG text truncated to {max_length} characters")
    
    return rag_text


def search_quests_by_rag_text(
    text_embedding: List[float],
    match_threshold: float = 0.65,
    match_count: int = 10,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None
) -> List[Dict]:
    try:
        filter_dict = {"type": {"$eq": "quest_text"}}
        
        similar_quests = search_text_embeddings(
            text_embedding=text_embedding,
            match_threshold=match_threshold,
            match_count=match_count * 2,
            filter_dict=filter_dict
        )
        
        if not similar_quests:
            logger.info("No quests found via RAG search")
            return []
        
        db = get_db()
        quest_ids = [q.get("quest_id") for q in similar_quests if q.get("quest_id")]
        
        if not quest_ids:
            return []
        
        quests_result = db.table("quests") \
            .select("*, places(*)") \
            .in_("id", quest_ids) \
            .eq("is_active", True) \
            .execute()
        
        quests_dict = {}
        for quest in quests_result.data:
            quest_id = quest.get("id")
            if quest_id:
                quests_dict[quest_id] = quest
        
        results = []
        for rag_result in similar_quests:
            quest_id = rag_result.get("quest_id")
            if not quest_id or quest_id not in quests_dict:
                continue
            
            quest = quests_dict[quest_id]
            
            if latitude and longitude and radius_km:
                quest_lat = quest.get("latitude")
                quest_lon = quest.get("longitude")
                if quest_lat and quest_lon:
                    import math
                    R = 6371
                    lat1_rad = math.radians(latitude)
                    lat2_rad = math.radians(float(quest_lat))
                    delta_lat = math.radians(float(quest_lat) - latitude)
                    delta_lon = math.radians(float(quest_lon) - longitude)
                    a = math.sin(delta_lat / 2) ** 2 + \
                        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    distance = R * c
                    if distance > radius_km:
                        continue
                    quest["distance_km"] = round(distance, 2)
            
            place = quest.get("places")
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]
                elif isinstance(place, dict) and len(place) > 0:
                    pass
                else:
                    place = None
            
            if place and isinstance(place, dict):
                quest["place"] = place
                if not quest.get("category") and place.get("category"):
                    quest["category"] = place["category"]
                if not quest.get("district") and place.get("district"):
                    quest["district"] = place["district"]
            
            quest.pop("places", None)
            
            results.append({
                "id": quest_id,
                "quest": quest,
                "similarity": rag_result.get("similarity", 0.0),
                "rag_text": rag_result.get("rag_text", "")
            })
        
        results.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        
        return results[:match_count]
    
    except Exception as e:
        logger.error(f"Error searching quests by RAG: {e}", exc_info=True)
        return []


def upsert_quest_text_embedding(
    quest_id: int,
    rag_text: str,
    metadata: Optional[Dict] = None
) -> Optional[str]:
    try:
        text_embedding = generate_text_embedding(rag_text)
        if not text_embedding:
            logger.warning(f"Failed to generate embedding for quest {quest_id}")
            return None
        
        embedding_metadata = {
            "type": "quest_text",
            "quest_id": quest_id,
            "rag_text": rag_text[:1000] if rag_text else ""
        }
        
        if metadata:
            embedding_metadata.update(metadata)
        
        vector_id = f"quest-text-{quest_id}"
        result = upsert_text_embedding(
            place_id=str(quest_id),
            text_embedding=text_embedding,
            rag_text=rag_text,
            metadata=embedding_metadata
        )
        
        if result:
            logger.info(f"Quest RAG embedding saved: quest_id={quest_id}")
            return vector_id
        else:
            logger.warning(f"Failed to save quest RAG embedding: quest_id={quest_id}")
            return None
    
    except Exception as e:
        logger.error(f"Error upserting quest text embedding: {e}", exc_info=True)
        return None


def generate_and_save_quest_rag(quest_id: int) -> bool:
    try:
        db = get_db()
        
        quest_result = db.table("quests") \
            .select("*, places(*)") \
            .eq("id", quest_id) \
            .single() \
            .execute()
        
        if not quest_result.data:
            logger.warning(f"Quest {quest_id} not found")
            return False
        
        quest = dict(quest_result.data)
        place = quest.pop("places", None)
        if isinstance(place, list) and len(place) > 0:
            place = place[0]
        
        rag_text = generate_quest_rag_text(quest, place)
        
        if not rag_text:
            logger.warning(f"Failed to generate RAG text for quest {quest_id}")
            return False
        
        vector_id = upsert_quest_text_embedding(quest_id, rag_text)
        
        return vector_id is not None
    
    except Exception as e:
        logger.error(f"Error generating and saving quest RAG: {e}", exc_info=True)
        return False
