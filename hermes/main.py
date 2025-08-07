"""Main entry point for Project Hermes."""

import logging
import sys
from pathlib import Path

from .config import LOGS_DIR, MAX_TOTAL_ARTICLES
from .fetcher import fetch_articles
from .filter import filter_articles, categorize_articles
from .summarizer import summarize_articles
from .writer import write_digest


def setup_logging() -> None:
    """Configure logging for the application."""
    log_file = LOGS_DIR / "hermes.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_pipeline(output_format: str = "markdown") -> Path:
    """
    Run the complete Hermes news digest pipeline.
    
    Args:
        output_format: Output format ("markdown", "html", "json").
        
    Returns:
        Path to the generated digest file.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting Hermes news digest pipeline")
    
    try:
        # Step 1: Fetch articles
        logger.info("Fetching articles...")
        articles = fetch_articles()
        
        if not articles:
            logger.error("No articles fetched")
            return None
        
        # Step 2: Filter unwanted content
        logger.info("Filtering articles...")
        articles = filter_articles(articles)
        
        # Limit total articles
        if len(articles) > MAX_TOTAL_ARTICLES:
            articles = articles[:MAX_TOTAL_ARTICLES]
            logger.info(f"Limited to {MAX_TOTAL_ARTICLES} articles")
        
        # Step 3: Categorize articles
        logger.info("Categorizing articles...")
        articles = categorize_articles(articles)
        
        # Step 4: Summarize articles
        logger.info("Summarizing articles...")
        articles = summarize_articles(articles)
        
        # Step 5: Write digest
        logger.info(f"Writing digest in {output_format} format...")
        digest_path = write_digest(articles, output_format)
        
        logger.info(f"Pipeline completed successfully. Digest: {digest_path}")
        return digest_path
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Hermes news digest")
    parser.add_argument(
        "--format", 
        choices=["markdown", "html", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        digest_path = run_pipeline(args.format)
        if digest_path:
            print(f"\n✅ Digest generated: {digest_path}")
        else:
            print("\n❌ Failed to generate digest")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
