This is my basic directory layout
```aiignore
alchemetra/

├── pyproject.toml
│
├── src/
│   └── alchemetra/
│
│       ├── app/
│       │
│       ├── project/
│       │   ├── project.py
│       │   └── project_manager.py
│       │
│       ├── data/
│       │   ├── dataset.py
│       │   ├── artifact.py
│       │   └── datasource.py
│       │
│       ├── annotations/
│       │   ├── base.py
│       │   ├── peak.py
│       │   ├── roi.py
│       │   └── separator.py
│       │
│       ├── workflow/
│       │   ├── graph.py
│       │   ├── node.py
│       │   ├── edge.py
│       │   └── execution.py
│       │
│       ├── provenance/
│       │   ├── lineage.py
│       │   └── tracker.py
│       │
│       ├── commands/
│       │   ├── base.py
│       │   └── manager.py
│       │
│       ├── services/
│       │   ├── annotation_service.py
│       │   ├── workflow_service.py
│       │   └── dataset_service.py
│       │
│       ├── ui/
│       │
│       └── utils/
│
└── tests/
```

Base struckture of a Project:
Project
 - Raw Data
 - Derived Data
 - Workflow
 - User Annotations
 - Results
