@staticmethod
def get_or_create_quote_type():
    """Get or create a Quote document type"""
    try:
        quote_type = DocumentType.query.filter_by(name='Quote').first()
        if not quote_type:
            quote_type = DocumentType(
                name='Quote',
                description='System generated quotes'
            )
            db.session.add(quote_type)
            db.session.commit()
        return quote_type
    except Exception as e:
        print(f"Error getting/creating quote type: {str(e)}")
        # Return a default document type if Quote type fails
        return DocumentType.query.first()