"""카테고리 경로 검증 및 업데이트 스크립트

VISIT SEOUL API에서 실제 카테고리 목록을 가져와서
CATEGORY_DATASET_INFO에 정의된 path들이 제대로 매칭되는지 확인하고,
누락된 카테고리나 잘못된 경로를 찾아냅니다.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.visit_seoul_api import (
    get_category_list,
    normalize_category_path,
    CATEGORY_DATASET_INFO
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_category_structure(categories: List[Dict]) -> Dict:
    """
    카테고리 구조 분석
    
    Returns:
        분석 결과 딕셔너리
    """
    analysis = {
        "total_categories": len(categories),
        "by_path": defaultdict(list),
        "by_name": defaultdict(list),
        "all_paths": set(),
        "all_names": set(),
        "category_tree": defaultdict(lambda: defaultdict(list))
    }
    
    for cat in categories:
        ctgry_nm = cat.get("ctgry_nm", "").strip()
        ctgry_path_raw = cat.get("ctgry_path") or ctgry_nm
        ctgry_path = normalize_category_path(ctgry_path_raw)
        category_sn = cat.get("com_ctgry_sn")
        
        if not category_sn:
            continue
        
        analysis["by_path"][ctgry_path].append({
            "sn": category_sn,
            "name": ctgry_nm,
            "raw": cat
        })
        
        analysis["by_name"][ctgry_nm].append({
            "sn": category_sn,
            "path": ctgry_path,
            "raw": cat
        })
        
        analysis["all_paths"].add(ctgry_path)
        analysis["all_names"].add(ctgry_nm)
        
        # 트리 구조 생성
        path_parts = ctgry_path.split(" > ")
        if len(path_parts) >= 1:
            parent = path_parts[0]
            if len(path_parts) >= 2:
                child = " > ".join(path_parts[1:])
                analysis["category_tree"][parent][child].append({
                    "sn": category_sn,
                    "name": ctgry_nm,
                    "full_path": ctgry_path
                })
            else:
                analysis["category_tree"][parent]["_root"].append({
                    "sn": category_sn,
                    "name": ctgry_nm,
                    "full_path": ctgry_path
                })
    
    return analysis


def check_path_matching(category: str, category_info: Dict, analysis: Dict, lang_code_id: str = "en") -> Dict:
    """
    특정 카테고리의 path 매칭 상태 확인
    
    Returns:
        매칭 결과 딕셔너리
    """
    is_english = lang_code_id == "en"
    
    if is_english:
        include_paths = [normalize_category_path(p) for p in category_info.get("include_paths_en", [])]
        include_prefixes = [normalize_category_path(p) for p in category_info.get("include_prefixes_en", [])]
    else:
        include_paths = [normalize_category_path(p) for p in category_info.get("include_paths", [])]
        include_prefixes = [normalize_category_path(p) for p in category_info.get("include_prefixes", [])]
    
    result = {
        "category": category,
        "lang": lang_code_id,
        "defined_paths": include_paths,
        "defined_prefixes": include_prefixes,
        "exact_matches": [],
        "prefix_matches": [],
        "not_found": [],
        "suggestions": []
    }
    
    all_api_paths = analysis["all_paths"]
    
    # 정확한 경로 매칭 확인
    for defined_path in include_paths:
        if defined_path in all_api_paths:
            result["exact_matches"].append(defined_path)
        else:
            result["not_found"].append(defined_path)
            # 유사한 경로 찾기
            suggestions = find_similar_paths(defined_path, all_api_paths)
            result["suggestions"].extend(suggestions)
    
    # Prefix 매칭 확인
    for defined_prefix in include_prefixes:
        matching_paths = [p for p in all_api_paths if p.startswith(defined_prefix) or p.startswith(defined_prefix + " > ")]
        if matching_paths:
            result["prefix_matches"].extend(matching_paths)
        else:
            result["not_found"].append(f"{defined_prefix} (prefix)")
            suggestions = find_similar_paths(defined_prefix, all_api_paths)
            result["suggestions"].extend(suggestions)
    
    return result


def find_similar_paths(target_path: str, all_paths: Set[str], max_results: int = 5) -> List[str]:
    """유사한 경로 찾기"""
    target_lower = target_path.lower()
    target_parts = [p.strip().lower() for p in target_path.split(">")]
    
    scored_paths = []
    for path in all_paths:
        path_lower = path.lower()
        path_parts = [p.strip().lower() for p in path.split(">")]
        
        score = 0
        # 정확한 부분 문자열 매칭
        if target_lower in path_lower or path_lower in target_lower:
            score += 10
        
        # 공통 부분 개수
        common_parts = set(target_parts) & set(path_parts)
        score += len(common_parts) * 2
        
        # 마지막 부분 매칭 (더 중요)
        if target_parts and path_parts:
            if target_parts[-1] in path_parts[-1] or path_parts[-1] in target_parts[-1]:
                score += 5
        
        if score > 0:
            scored_paths.append((score, path))
    
    scored_paths.sort(reverse=True, key=lambda x: x[0])
    return [path for _, path in scored_paths[:max_results]]


def generate_category_tree_report(analysis: Dict) -> str:
    """카테고리 트리 구조 리포트 생성"""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("VISIT SEOUL API 카테고리 트리 구조")
    lines.append("=" * 80)
    
    for parent in sorted(analysis["category_tree"].keys()):
        lines.append(f"\n[{parent}]")
        children = analysis["category_tree"][parent]
        
        # 루트 레벨 카테고리
        if "_root" in children:
            for item in children["_root"]:
                lines.append(f"  └─ {item['name']} (SN: {item['sn']})")
        
        # 하위 카테고리
        for child_path, items in sorted(children.items()):
            if child_path == "_root":
                continue
            lines.append(f"  └─ {child_path}")
            for item in items:
                lines.append(f"      └─ {item['name']} (SN: {item['sn']}, Path: {item['full_path']})")
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify and analyze VISIT SEOUL category paths")
    parser.add_argument(
        "--lang-code",
        type=str,
        default="en",
        choices=["ko", "en", "ja", "zh"],
        help="Language code for category analysis (default: en)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path for detailed analysis results"
    )
    parser.add_argument(
        "--show-tree",
        action="store_true",
        help="Show full category tree structure"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("VISIT SEOUL 카테고리 경로 검증 스크립트")
    logger.info("=" * 80)
    
    if not os.getenv("VISIT_SEOUL_API_KEY"):
        logger.error("VISIT_SEOUL_API_KEY environment variable is required")
        sys.exit(1)
    
    # API에서 카테고리 목록 가져오기
    logger.info(f"Fetching category list from API (lang: {args.lang_code})...")
    categories = get_category_list(lang_code_id=args.lang_code)
    
    if not categories:
        logger.error("Failed to fetch categories from API")
        sys.exit(1)
    
    logger.info(f"Found {len(categories)} categories from API")
    
    # 카테고리 구조 분석
    logger.info("Analyzing category structure...")
    analysis = analyze_category_structure(categories)
    
    # 각 카테고리별 매칭 확인
    logger.info("\n" + "=" * 80)
    logger.info("카테고리별 경로 매칭 결과")
    logger.info("=" * 80)
    
    all_results = []
    for category, category_info in CATEGORY_DATASET_INFO.items():
        logger.info(f"\n[{category}]")
        logger.info(f"Description: {category_info.get('description', 'N/A')}")
        
        result = check_path_matching(category, category_info, analysis, args.lang_code)
        all_results.append(result)
        
        # 정확한 매칭
        if result["exact_matches"]:
            logger.info(f"  ✓ 정확한 매칭 ({len(result['exact_matches'])}개):")
            for path in result["exact_matches"]:
                logger.info(f"    - {path}")
        
        # Prefix 매칭
        if result["prefix_matches"]:
            logger.info(f"  ✓ Prefix 매칭 ({len(set(result['prefix_matches']))}개 경로):")
            for path in sorted(set(result["prefix_matches"]))[:10]:  # 최대 10개만 표시
                logger.info(f"    - {path}")
            if len(set(result["prefix_matches"])) > 10:
                logger.info(f"    ... and {len(set(result['prefix_matches'])) - 10} more")
        
        # 매칭 실패
        if result["not_found"]:
            logger.warning(f"  ✗ 매칭 실패 ({len(result['not_found'])}개):")
            for path in result["not_found"]:
                logger.warning(f"    - {path}")
        
        # 제안
        if result["suggestions"]:
            logger.info(f"  💡 제안된 경로:")
            for suggestion in result["suggestions"][:3]:  # 상위 3개만
                logger.info(f"    - {suggestion}")
    
    # 전체 카테고리 트리 구조 출력
    if args.show_tree:
        tree_report = generate_category_tree_report(analysis)
        logger.info(tree_report)
    
    # JSON 출력
    if args.output:
        output_data = {
            "analysis": {
                "total_categories": analysis["total_categories"],
                "unique_paths": len(analysis["all_paths"]),
                "unique_names": len(analysis["all_names"])
            },
            "category_matching_results": all_results,
            "category_tree": {
                parent: {
                    child: [
                        {"sn": item["sn"], "name": item["name"], "full_path": item["full_path"]}
                        for item in items
                    ]
                    for child, items in children.items()
                }
                for parent, children in analysis["category_tree"].items()
            },
            "all_paths": sorted(list(analysis["all_paths"])),
            "all_category_sns": {
                cat.get("com_ctgry_sn"): {
                    "name": cat.get("ctgry_nm"),
                    "path": normalize_category_path(cat.get("ctgry_path") or cat.get("ctgry_nm", ""))
                }
                for cat in categories
                if cat.get("com_ctgry_sn")
            }
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n상세 분석 결과가 {args.output}에 저장되었습니다.")
    
    # 요약
    logger.info("\n" + "=" * 80)
    logger.info("요약")
    logger.info("=" * 80)
    
    total_defined = sum(len(r["defined_paths"]) + len(r["defined_prefixes"]) for r in all_results)
    total_exact = sum(len(r["exact_matches"]) for r in all_results)
    total_prefix = sum(len(set(r["prefix_matches"])) for r in all_results)
    total_not_found = sum(len(r["not_found"]) for r in all_results)
    
    logger.info(f"총 정의된 경로/prefix: {total_defined}")
    logger.info(f"  - 정확한 매칭: {total_exact}")
    logger.info(f"  - Prefix 매칭: {total_prefix}")
    logger.info(f"  - 매칭 실패: {total_not_found}")
    logger.info(f"\nAPI에서 발견된 총 카테고리 수: {analysis['total_categories']}")
    logger.info(f"고유 경로 수: {len(analysis['all_paths'])}")
    
    if total_not_found > 0:
        logger.warning(f"\n⚠️  {total_not_found}개의 경로가 API에서 찾을 수 없습니다.")
        logger.warning("위의 제안된 경로를 확인하여 CATEGORY_DATASET_INFO를 업데이트하세요.")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

