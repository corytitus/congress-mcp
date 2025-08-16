#!/usr/bin/env python3
"""
Import Supporting Documentation into Document Store
Imports valuable Congressional documentation from the supportingDocumentation folder
"""

import os
import sys
from pathlib import Path
from document_store import DocumentStore
import json

def import_key_documents():
    """Import key Congressional documentation files"""
    
    store = DocumentStore()
    base_path = Path("/Users/corytitus/Documents/GitHub/supportingDocumentation")
    
    if not base_path.exists():
        print(f"❌ Supporting documentation folder not found at {base_path}")
        return False
    
    # Define key documents to import
    documents_to_import = [
        # User Guides
        {
            "path": "bill-status-main/BILLSTATUS-XML_User-Guide-v1.pdf",
            "title": "Bill Status XML User Guide",
            "description": "Complete guide to understanding Bill Status XML format",
            "category": "technical_guides",
            "tags": ["xml", "bill_status", "technical", "api"]
        },
        {
            "path": "bill-status-main/BILLSTATUS-XML_User_User-Guide.md",
            "title": "Bill Status XML User Guide (Markdown)",
            "description": "Markdown version of the Bill Status XML documentation",
            "category": "technical_guides",
            "tags": ["xml", "bill_status", "technical", "api", "markdown"]
        },
        {
            "path": "bulk-data-main/Bills-Summary-XML-User-Guide.md",
            "title": "Bills Summary XML User Guide",
            "description": "Guide to understanding Bills Summary XML format",
            "category": "technical_guides",
            "tags": ["xml", "bills", "summary", "technical"]
        },
        {
            "path": "bulk-data-main/Bills-XML-User-Guide.md",
            "title": "Bills XML User Guide",
            "description": "Comprehensive guide to Bills XML format",
            "category": "technical_guides",
            "tags": ["xml", "bills", "technical", "format"]
        },
        {
            "path": "uslm-main/USLM-User-Guide.pdf",
            "title": "USLM User Guide",
            "description": "United States Legislative Markup Language guide",
            "category": "technical_guides",
            "tags": ["uslm", "xml", "markup", "technical"]
        },
        {
            "path": "uslm-main/USLM-2_1-ReviewGuide.pdf",
            "title": "USLM 2.1 Review Guide",
            "description": "Review guide for USLM version 2.1",
            "category": "technical_guides",
            "tags": ["uslm", "xml", "version_2.1", "technical"]
        },
        
        # API Documentation
        {
            "path": "api-main/README.md",
            "title": "Congress.gov API Documentation",
            "description": "Official API documentation for Congress.gov",
            "category": "api_documentation",
            "tags": ["api", "congress.gov", "documentation", "rest"]
        },
        {
            "path": "link-service-main/README.md",
            "title": "Link Service Documentation",
            "description": "Documentation for the Congress.gov link service",
            "category": "api_documentation",
            "tags": ["api", "links", "service", "congress.gov"]
        },
        
        # Sample Bill Status Files (for reference)
        {
            "path": "118hr2670/BILLSTATUS-118hr2670.xml",
            "title": "Sample Bill Status - HR 2670 (118th Congress)",
            "description": "Example of complete bill status XML for HR 2670",
            "category": "samples",
            "tags": ["sample", "bill_status", "hr2670", "118th_congress", "xml"]
        },
        
        # Schema Files
        {
            "path": "uslm-main/USLM.xsd",
            "title": "USLM XML Schema",
            "description": "XML Schema Definition for USLM format",
            "category": "schemas",
            "tags": ["schema", "xsd", "uslm", "xml", "validation"]
        },
        {
            "path": "uslm-main/uslm-2.1.0.xsd",
            "title": "USLM 2.1.0 XML Schema",
            "description": "XML Schema Definition for USLM version 2.1.0",
            "category": "schemas",
            "tags": ["schema", "xsd", "uslm", "xml", "version_2.1.0"]
        },
        
        # Educational Materials
        {
            "path": "bill-status-main/meetings/BDTF_PublicMtg_BillStatusinBulk_December_2015.pdf",
            "title": "Bill Status in Bulk - Public Meeting (Dec 2015)",
            "description": "Public meeting presentation about bulk bill status data",
            "category": "presentations",
            "tags": ["presentation", "bulk_data", "bill_status", "meeting"]
        },
        {
            "path": "bill-status-main/meetings/Slides_BDTF_PublicMtg_BillStatusinBulk_April_2016.pdf",
            "title": "Bill Status in Bulk - Public Meeting (Apr 2016)",
            "description": "Follow-up presentation on bulk bill status implementation",
            "category": "presentations",
            "tags": ["presentation", "bulk_data", "bill_status", "meeting", "implementation"]
        }
    ]
    
    success_count = 0
    error_count = 0
    
    print(f"📚 Importing {len(documents_to_import)} key Congressional documents...")
    print("=" * 60)
    
    for doc_info in documents_to_import:
        file_path = base_path / doc_info["path"]
        
        if not file_path.exists():
            print(f"⚠️  File not found: {doc_info['path']}")
            error_count += 1
            continue
        
        try:
            # Read file content
            if file_path.suffix in ['.pdf', '.xml', '.xsd']:
                with open(file_path, 'rb') as f:
                    content = f.read()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
            
            # Store document
            doc_id = store.store_document(
                content=content,
                filename=file_path.name,
                title=doc_info["title"],
                description=doc_info["description"],
                category=doc_info["category"],
                tags=doc_info["tags"]
            )
            
            print(f"✅ Imported: {doc_info['title']}")
            print(f"   ID: {doc_id}")
            print(f"   Category: {doc_info['category']}")
            print(f"   Size: {len(content):,} bytes")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error importing {doc_info['title']}: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Import Summary:")
    print(f"   ✅ Successfully imported: {success_count} documents")
    if error_count > 0:
        print(f"   ❌ Failed imports: {error_count} documents")
    
    # Show categories
    print(f"\n📁 Document Categories:")
    categories = store.list_categories()
    for category in categories:
        docs = store.search_documents(category=category)
        print(f"   • {category}: {len(docs)} documents")
    
    return success_count > 0

def list_available_samples():
    """List available sample bill files"""
    base_path = Path("/Users/corytitus/Documents/GitHub/supportingDocumentation")
    
    print("\n📄 Available Sample Bills:")
    print("=" * 60)
    
    # HR 2670 samples
    hr2670_path = base_path / "118hr2670"
    if hr2670_path.exists():
        print("\n118th Congress - HR 2670 (Multiple versions):")
        for version_dir in sorted(hr2670_path.glob("BILLS-*")):
            if version_dir.is_dir():
                version_name = version_dir.name.replace("BILLS-118hr2670", "")
                print(f"   • {version_name}: {version_dir.name}")
    
    # 119th Congress templates
    hr119_path = base_path / "HR-119 XML Template"
    if hr119_path.exists():
        print("\n119th Congress - House Bill Templates:")
        for xml_file in sorted(hr119_path.glob("*.xml")):
            print(f"   • {xml_file.name}")
    
    s119_path = base_path / "S-119 XML Template"
    if s119_path.exists():
        print("\n119th Congress - Senate Bill Templates:")
        for xml_file in sorted(s119_path.glob("*.xml")):
            print(f"   • {xml_file.name}")
    
    # Bill status samples
    samples_path = base_path / "bill-status-main/samples"
    if samples_path.exists():
        print("\nBill Status Samples:")
        for category_dir in sorted(samples_path.glob("*")):
            if category_dir.is_dir():
                xml_files = list(category_dir.glob("*.xml"))
                if xml_files:
                    print(f"   • {category_dir.name}: {len(xml_files)} samples")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import Congressional supporting documentation"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import key documents')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available documents')
    
    args = parser.parse_args()
    
    if args.command == 'import':
        import_key_documents()
    elif args.command == 'list':
        list_available_samples()
    else:
        # Default action - import documents
        import_key_documents()
        list_available_samples()

if __name__ == "__main__":
    main()