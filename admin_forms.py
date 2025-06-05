
# admin_forms.py - Fixed Forms for Feature Management

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class FeatureForm(FlaskForm):
    name = StringField('Feature Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Feature Code', validators=[DataRequired(), Length(max=50)])
    description = TextAreaField('Description')
    category = SelectField('Category', choices=[
        ('dashboard', 'Dashboard'),
        ('reports', 'Reports'), 
        ('files', 'Files'),
        ('users', 'User Management'),
        ('analytics', 'Analytics'),
        ('api', 'API Access'),
        ('integrations', 'Integrations'),
        ('advanced', 'Advanced Features')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Feature')

class CompanyFeaturesManagementForm(FlaskForm):
    submit = SubmitField('Update Company Features')
    
    def __init__(self, company_id=None, *args, **kwargs):
        super(CompanyFeaturesManagementForm, self).__init__(*args, **kwargs)
        
        self._features = []
        
        if company_id:
            # Import here to avoid circular imports
            from models import Feature, Company
            
            self.company_id = company_id
            features = Feature.query.filter_by(is_active=True).order_by(Feature.category, Feature.name).all()
            
            # Get currently enabled features
            enabled_features = set()
            company = Company.query.get(company_id)
            if company:
                enabled_features = {f.code for f in company.get_enabled_features()}
            
            # Create form fields dynamically
            for feature in features:
                field_name = f'feature_{feature.code}'
                
                # Create the field and add it to the form
                field = BooleanField(
                    feature.name,
                    default=feature.code in enabled_features
                )
                
                # Add the field to the form
                setattr(self, field_name, field)
                
                # Store feature for template access
                self._features.append(feature)
    
    def get_features(self):
        """Get list of features for this form"""
        return self._features
