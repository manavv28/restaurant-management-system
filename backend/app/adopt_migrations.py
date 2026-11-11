"""Verify a manually initialized schema before explicitly adopting checksum migration history."""
import argparse,hashlib
from pathlib import Path
from sqlalchemy import inspect,text
from .database import Base,engine

def verify(db):
    inspector=inspect(db)
    for table in Base.metadata.sorted_tables:
        columns={c['name']:c for c in inspector.get_columns(table.name)}
        if set(columns)!=set(table.c.keys()):raise ValueError('Column mismatch: '+table.name)
        for column in table.c:
            actual=columns[column.name]
            if actual['nullable']!=column.nullable or actual['type']._type_affinity!=column.type._type_affinity:
                raise ValueError('Column definition mismatch: '+table.name+'.'+column.name)
        if set(inspector.get_pk_constraint(table.name)['constrained_columns'])!=set(c.name for c in table.primary_key):raise ValueError('Primary key mismatch: '+table.name)
        actual_fks={(tuple(fk['constrained_columns']),fk['referred_table'],tuple(fk['referred_columns']),fk.get('options',{}).get('ondelete')) for fk in inspector.get_foreign_keys(table.name)}
        expected_fks={(tuple(c.name for c in fk.columns),next(iter(fk.elements)).column.table.name,tuple(e.column.name for e in fk.elements),fk.ondelete) for fk in table.foreign_key_constraints}
        if expected_fks!=actual_fks:raise ValueError('Foreign key mismatch: '+table.name)
        from sqlalchemy import UniqueConstraint,CheckConstraint
        uniques={tuple(c.name for c in constraint.columns) for constraint in table.constraints if isinstance(constraint,UniqueConstraint)}
        if not uniques.issubset({tuple(c['column_names']) for c in inspector.get_unique_constraints(table.name)}):raise ValueError('Unique constraint missing: '+table.name)
        checks={constraint.name for constraint in table.constraints if isinstance(constraint,CheckConstraint)}
        if not checks.issubset({c['name'] for c in inspector.get_check_constraints(table.name)}):raise ValueError('Check constraint missing: '+table.name)
        indexes={index.name for index in table.indexes}
        if not indexes.issubset({index['name'] for index in inspector.get_indexes(table.name)}):raise ValueError('Index missing: '+table.name)
        if not db.scalar(text("select relrowsecurity from pg_class where oid=to_regclass(:name)"),{'name':'public.'+table.name}):raise ValueError('RLS missing: '+table.name)
        for role in ('anon','authenticated'):
            if db.scalar(text("select has_table_privilege(:role,:name,'SELECT,INSERT,UPDATE,DELETE')"),{'role':role,'name':'public.'+table.name}):raise ValueError('Browser access present: '+table.name)

def adopt(directory,execute=False):
    if engine.dialect.name!='postgresql':raise ValueError('PostgreSQL required')
    files=sorted(Path(directory).glob('*.sql'))
    if not files:raise ValueError('No migrations found')
    with engine.begin() as db:
        db.execute(text('select pg_advisory_xact_lock(9100801)'))
        verify(db)
        if execute:
            db.execute(text('CREATE TABLE IF NOT EXISTS public.biteai_migrations (name text PRIMARY KEY,sha256 text NOT NULL)'))
            db.execute(text('ALTER TABLE public.biteai_migrations ENABLE ROW LEVEL SECURITY'))
            db.execute(text('REVOKE ALL ON TABLE public.biteai_migrations FROM PUBLIC,anon,authenticated'))
            previous=dict(db.execute(text('select name,sha256 from biteai_migrations')).all())
            for file in files:
                digest=hashlib.sha256(file.read_bytes()).hexdigest()
                if file.name in previous and previous[file.name]!=digest:raise ValueError('Checksum mismatch: '+file.name)
                db.execute(text('insert into biteai_migrations(name,sha256) values (:name,:sha) on conflict(name) do nothing'),{'name':file.name,'sha':digest})
    return {'verified_tables':len(Base.metadata.tables),'adopted':execute}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',default='supabase/migrations');parser.add_argument('--adopt',action='store_true');args=parser.parse_args()
    print(adopt(args.directory,args.adopt))
