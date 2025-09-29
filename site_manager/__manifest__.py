{
    "name": "Site Manager (Project -> Site, Task -> Milestone)",
    "version": "16.0.0.1.0",
    "summary": "Rename Project->Site, Task->Milestone. Add dynamic-stage requirements.",
    "description": "Case 1 & 2 implementation for Odoo16: extra fields, dynamic requirement config and validation on stage change.",
    "author": "Carlos Estrada",
    "license": "AGPL-3",
    "category": "Project",
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "views/site_views.xml",
        "views/requirement_views.xml",
        "views/project_site_views.xml",
    ],
    "installable": True,
    "application": False,
}
