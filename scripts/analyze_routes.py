#!/usr/bin/env python3
"""
Flask Route Analyzer
This script will analyze your app.py file and show all routes organized by function area
"""

import re
import sys
from pathlib import Path

def analyze_routes(file_path):
    """Analyze routes in a Flask app.py file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found!")
        return None
    
    # Find all route decorators and their functions
    route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[([^\]]+)\])?\)\s*(?:@\w+\s*)*\s*def\s+(\w+)'
    
    routes = re.findall(route_pattern, content, re.MULTILINE)
    
    # Organize routes by category
    categories = {
        'Authentication': [],
        'Admin': [],
        'User Management': [],
        'Company Management': [],
        'Tender Management': [],
        'Reports': [],
        'Documents': [],
        'API': [],
        'Other': []
    }
    
    for route_path, methods, function_name in routes:
        methods_str = methods.replace("'", "").replace('"', '') if methods else 'GET'
        
        # Categorize based on route path and function name
        if any(keyword in route_path.lower() or keyword in function_name.lower() 
               for keyword in ['login', 'logout', 'register', 'auth']):
            categories['Authentication'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['admin']):
            categories['Admin'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['user', 'profile']):
            categories['User Management'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['company', 'companies']):
            categories['Company Management'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['tender', 'bid']):
            categories['Tender Management'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['report', 'analytics', 'dashboard']):
            categories['Reports'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['document', 'file', 'upload']):
            categories['Documents'].append((route_path, methods_str, function_name))
        elif any(keyword in route_path.lower() or keyword in function_name.lower() 
                for keyword in ['api', 'json']):
            categories['API'].append((route_path, methods_str, function_name))
        else:
            categories['Other'].append((route_path, methods_str, function_name))
    
    return categories

def print_analysis(categories):
    """Print the route analysis"""
    total_routes = sum(len(routes) for routes in categories.values())
    
    print(f"\n{'='*60}")
    print(f"FLASK ROUTE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total Routes Found: {total_routes}")
    print(f"{'='*60}\n")
    
    for category, routes in categories.items():
        if routes:  # Only show categories that have routes
            print(f"📁 {category.upper()} ({len(routes)} routes)")
            print("-" * 50)
            for route_path, methods, function_name in routes:
                print(f"  {methods:12} {route_path:30} -> {function_name}()")
            print()

def suggest_blueprint_structure(categories):
    """Suggest how to organize routes into blueprints"""
    print(f"\n{'='*60}")
    print(f"SUGGESTED BLUEPRINT STRUCTURE")
    print(f"{'='*60}")
    
    blueprint_suggestions = {
        'auth_bp': ['Authentication'],
        'admin_bp': ['Admin', 'User Management'],
        'company_bp': ['Company Management'],
        'tender_bp': ['Tender Management'],
        'report_bp': ['Reports'],
        'document_bp': ['Documents'],
        'api_bp': ['API'],
        'main_bp': ['Other']
    }
    
    for blueprint_name, category_list in blueprint_suggestions.items():
        total_routes = sum(len(categories.get(cat, [])) for cat in category_list)
        if total_routes > 0:
            print(f"\n📦 {blueprint_name} ({total_routes} routes)")
            print(f"   File: routes/{blueprint_name.replace('_bp', '')}.py")
            for category in category_list:
                if categories.get(category):
                    print(f"   - {category}: {len(categories[category])} routes")

if __name__ == "__main__":
    file_path = "app.py"  # Default to app.py in current directory
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    print(f"Analyzing routes in: {file_path}")
    
    categories = analyze_routes(file_path)
    
    if categories:
        print_analysis(categories)
        suggest_blueprint_structure(categories)
        
        print(f"\n{'='*60}")
        print("NEXT STEPS:")
        print(f"{'='*60}")
        print("1. Run this script to see your current route structure")
        print("2. Create the suggested blueprint files")
        print("3. Move routes to appropriate blueprint files")
        print("4. Update app.py to register blueprints")
        print("5. Test that all routes still work")
        
    else:
        print("Could not analyze the file. Please check the file path and try again.")