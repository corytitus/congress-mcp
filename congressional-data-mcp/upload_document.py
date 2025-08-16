#!/usr/bin/env python3
"""
Document Upload Script for Congressional MCP Server
Upload PDFs, text files, and other documents to the knowledge base
"""

import os
import sys
import argparse
from pathlib import Path
from document_store import DocumentStore

def upload_file(filepath: str, 
                title: str = None,
                description: str = None,
                category: str = None,
                tags: str = None):
    """Upload a file to the document store"""
    
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    # Initialize document store
    store = DocumentStore()
    
    # Read file content
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else []
    
    # Store document
    doc_id = store.store_document(
        content=content,
        filename=filepath.name,
        title=title or filepath.stem,
        description=description,
        category=category,
        tags=tag_list
    )
    
    print(f"✅ Document uploaded successfully!")
    print(f"   ID: {doc_id}")
    print(f"   Title: {title or filepath.name}")
    print(f"   Category: {category or 'uncategorized'}")
    print(f"   Tags: {', '.join(tag_list) if tag_list else 'none'}")
    print(f"   Size: {len(content):,} bytes")
    
    return True

def upload_directory(directory: str, category: str = None):
    """Upload all documents in a directory"""
    dirpath = Path(directory)
    if not dirpath.exists():
        print(f"❌ Directory not found: {dirpath}")
        return False
    
    # Find all documents
    patterns = ['*.pdf', '*.txt', '*.md', '*.json', '*.html']
    files = []
    for pattern in patterns:
        files.extend(dirpath.glob(pattern))
    
    if not files:
        print(f"❌ No documents found in {dirpath}")
        return False
    
    print(f"Found {len(files)} documents to upload...")
    
    success_count = 0
    for filepath in files:
        print(f"\nUploading: {filepath.name}")
        
        # Auto-detect category from subdirectory
        if not category and filepath.parent != dirpath:
            category = filepath.parent.name
        
        success = upload_file(
            str(filepath),
            title=filepath.stem.replace('_', ' ').title(),
            category=category
        )
        
        if success:
            success_count += 1
    
    print(f"\n📊 Summary: {success_count}/{len(files)} documents uploaded successfully")
    return success_count > 0

def list_documents():
    """List all documents in the store"""
    store = DocumentStore()
    documents = store.search_documents()
    
    if not documents:
        print("No documents found in the store")
        return
    
    print(f"\n📚 Document Library ({len(documents)} documents)")
    print("=" * 60)
    
    # Group by category
    by_category = {}
    for doc in documents:
        cat = doc.get('category', 'uncategorized')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(doc)
    
    for category, docs in sorted(by_category.items()):
        print(f"\n{category.upper()}")
        print("-" * 40)
        for doc in docs:
            size_kb = doc['size'] / 1024
            print(f"  [{doc['id']}] {doc['title']}")
            print(f"         {size_kb:.1f} KB | {doc.get('filename', 'unknown')}")
            if doc.get('tags'):
                print(f"         Tags: {', '.join(doc['tags'])}")

def search_documents(query: str):
    """Search for documents"""
    store = DocumentStore()
    results = store.search_documents(query=query)
    
    if not results:
        print(f"No documents found matching '{query}'")
        return
    
    print(f"\n🔍 Search Results for '{query}' ({len(results)} matches)")
    print("=" * 60)
    
    for doc in results:
        print(f"\n[{doc['id']}] {doc['title']}")
        if doc.get('description'):
            print(f"  {doc['description']}")
        print(f"  Category: {doc.get('category', 'uncategorized')}")
        if doc.get('tags'):
            print(f"  Tags: {', '.join(doc['tags'])}")

def main():
    parser = argparse.ArgumentParser(
        description="Upload and manage documents in the Congressional MCP knowledge base"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Upload file command
    upload_parser = subparsers.add_parser('upload', help='Upload a document')
    upload_parser.add_argument('file', help='Path to file to upload')
    upload_parser.add_argument('--title', help='Document title')
    upload_parser.add_argument('--description', help='Document description')
    upload_parser.add_argument('--category', help='Category (e.g., legislative_process, rules)')
    upload_parser.add_argument('--tags', help='Comma-separated tags')
    
    # Upload directory command
    dir_parser = subparsers.add_parser('upload-dir', help='Upload all documents in a directory')
    dir_parser.add_argument('directory', help='Path to directory')
    dir_parser.add_argument('--category', help='Category for all documents')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all documents')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search documents')
    search_parser.add_argument('query', help='Search query')
    
    # Load defaults command
    load_parser = subparsers.add_parser('load-defaults', help='Load default Congressional documents')
    
    args = parser.parse_args()
    
    if args.command == 'upload':
        upload_file(
            args.file,
            title=args.title,
            description=args.description,
            category=args.category,
            tags=args.tags
        )
    
    elif args.command == 'upload-dir':
        upload_directory(args.directory, category=args.category)
    
    elif args.command == 'list':
        list_documents()
    
    elif args.command == 'search':
        search_documents(args.query)
    
    elif args.command == 'load-defaults':
        from document_store import load_default_documents
        load_default_documents()
        print("✅ Default Congressional documents loaded")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()