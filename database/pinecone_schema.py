#!/usr/bin/env python3
"""Pinecone Schema Setup"""

import os
import sys
import time
import hashlib
import logging
from datetime import datetime
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

INDEX_NAME = "quest-of-seoul"
DIMENSION = 512
METRIC = "cosine"
CLOUD = "aws"
REGION = "us-east-1"


class PineconeSchemaManager:
    
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY not found")
        
        self.pc = Pinecone(api_key=api_key)
        self.index_name = INDEX_NAME
        logger.info(f"Pinecone client initialized")
    
    @staticmethod
    def print_header(title: str):
        logger.info("=" * 70)
        logger.info(f"  {title}")
        logger.info("=" * 70)
    
    def setup_pinecone_schema(self, insert_sample_data: bool = True) -> bool:
        self.print_header("Setup Pinecone Schema")
        
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info("Creating new index...")
                logger.info(f"Dimension: {DIMENSION}, Metric: {METRIC}")
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=DIMENSION,
                    metric=METRIC,
                    spec=ServerlessSpec(cloud=CLOUD, region=REGION)
                )
                
                logger.info("Index created")
                time.sleep(10)
            else:
                logger.info("Index already exists - Skipping")
                index = self.pc.Index(self.index_name)
                stats = index.describe_index_stats()
                logger.info(f"Current vectors: {stats.get('total_vector_count', 0)}")
            
            index = self.pc.Index(self.index_name)
            stats = index.describe_index_stats()
            vector_count = stats.get('total_vector_count', 0)
            
            if vector_count == 0 and insert_sample_data:
                logger.info("Inserting sample data...")
                
                sample_places = [
                    {
                        "place_id": "place-001-gyeongbokgung",
                        "place_name": "Gyeongbokgung Palace",
                        "category": "History",
                        "image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
                        "latitude": 37.579617,
                        "longitude": 126.977041,
                        "source": "dataset"
                    },
                    {
                        "place_id": "place-002-namsan-tower",
                        "place_name": "N Seoul Tower",
                        "category": "Attractions",
                        "image_url": "https://ak-d.tripcdn.com/images/100v0z000000nkadwE2AA_C_1200_800_Q70.webp",
                        "latitude": 37.551169,
                        "longitude": 126.988227,
                        "source": "dataset"
                    },
                    {
                        "place_id": "place-003-gwanghwamun",
                        "place_name": "Gwanghwamun Square",
                        "category": "Attractions",
                        "image_url": "https://ak-d.tripcdn.com/images/01051120008c32dlbE44A.webp",
                        "latitude": 37.572889,
                        "longitude": 126.976849,
                        "source": "dataset"
                    },
                    {
                        "place_id": "place-004-myeongdong-cathedral",
                        "place_name": "Myeongdong Cathedral",
                        "category": "Culture",
                        "image_url": "https://ak-d.tripcdn.com/images/100f1f000001gqchv1B53.webp",
                        "latitude": 37.563600,
                        "longitude": 126.986870,
                        "source": "dataset"
                    },
                    {
                        "place_id": "place-005-bukchon-hanok",
                        "place_name": "Bukchon Hanok Village",
                        "category": "Culture",
                        "image_url": "https://ak-d.tripcdn.com/images/100p11000000r4rhv9EF4.jpg",
                        "latitude": 37.582306,
                        "longitude": 126.985302,
                        "source": "dataset"
                    }
                ]
                
                logger.info(f"Preparing {len(sample_places)} vectors...")
                
                vectors_to_upsert = []
                
                for idx, place in enumerate(sample_places, 1):
                    import random
                    random.seed(idx)
                    dummy_vector = [random.uniform(-1, 1) for _ in range(DIMENSION)]
                    
                    vector_id = f"vec-{place['place_id']}"
                    image_hash = hashlib.sha256(place['image_url'].encode()).hexdigest()[:32]
                    
                    metadata = {
                        "place_id": place["place_id"],
                        "place_name": place["place_name"],
                        "category": place["category"],
                        "image_url": place["image_url"],
                        "image_hash": image_hash,
                        "source": place["source"],
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    }
                    
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": dummy_vector,
                        "metadata": metadata
                    })
                    
                    logger.info(f"[{idx}/{len(sample_places)}] {place['place_name']}")
                
                logger.info("Upserting vectors...")
                index.upsert(vectors=vectors_to_upsert)
                logger.info("Sample data inserted")
                
                time.sleep(2)
            elif vector_count == 0 and not insert_sample_data:
                logger.info("Skipping sample data insertion (insert_sample_data=False)")
            else:
                logger.info(f"Data already exists ({vector_count} vectors)")
            
            logger.info("Running test...")
            stats = index.describe_index_stats()
            logger.info(f"Dimension: {stats.get('dimension')}, Vectors: {stats.get('total_vector_count', 0)}")
            
            import random
            random.seed(42)
            query_vector = [random.uniform(-1, 1) for _ in range(DIMENSION)]
            results = index.query(vector=query_vector, top_k=3, include_metadata=True)
            
            if results.matches:
                logger.info(f"Query test passed - Found {len(results.matches)} results")
                for i, match in enumerate(results.matches[:3], 1):
                    logger.info(f"{i}. {match.metadata.get('place_name')}")
            
            self.print_header("Setup Complete")
            logger.info("Pinecone is ready")
            
            return True
        
        except Exception as e:
            logger.error(f"Setup error: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Pinecone schema")
    parser.add_argument(
        "--no-sample-data",
        action="store_true",
        help="Skip inserting sample data"
    )
    
    args = parser.parse_args()
    
    try:
        manager = PineconeSchemaManager()
        success = manager.setup_pinecone_schema(insert_sample_data=not args.no_sample_data)
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
