import warnings
import re

from peewee import Model, AutoField, BareField, CompositeKey, DeferredForeignKey, \
    ForeignKeyField, IntegerField, SQL
from playhouse.reflection import Introspector


class UnknownField(object):
    pass


def pluralize(word):
    if re.search('[sxz]$', word) or re.search('[^aeioudgkprt]h$', word):
        return re.sub('$', 'es', word)
    elif re.search('[aeiou]y$', word):
        return re.sub('y$', 'ies', word)
    else:
        return word + 's'


class PatchedIntrospector(Introspector):
    def generate_models(self, skip_invalid=False, table_names=None,
                        literal_column_names=False, bare_fields=False,
                        include_views=False):
        database = self.introspect(table_names, literal_column_names,
                                   include_views)
        models = {}

        class BaseModel(Model):
            class Meta:
                database = self.metadata.database
                schema = self.schema

        pending = set()

        def _create_model(table, models):
            pending.add(table)
            for foreign_key in database.foreign_keys[table]:
                dest = foreign_key.dest_table

                if dest not in models and dest != table:
                    if dest in pending:
                        warnings.warn('Possible reference cycle found between '
                                      '%s and %s' % (table, dest))
                    else:
                        _create_model(dest, models)

            primary_keys = []
            columns = database.columns[table]
            for column_name, column in columns.items():
                if column.primary_key:
                    primary_keys.append(column.name)

            multi_column_indexes = database.multi_column_indexes(table)
            column_indexes = database.column_indexes(table)

            class Meta:
                indexes = multi_column_indexes
                table_name = table

            # Fix models with multi-column primary keys.
            composite_key = False
            if len(primary_keys) == 0:
                primary_keys = columns.keys()
            if len(primary_keys) > 1:
                Meta.primary_key = CompositeKey(*[
                    field.name for col, field in columns.items()
                    if col in primary_keys])
                composite_key = True

            attrs = {'Meta': Meta}
            for column_name, column in columns.items():
                FieldClass = column.field_class
                if FieldClass is not ForeignKeyField and bare_fields:
                    FieldClass = BareField
                elif FieldClass is UnknownField:
                    FieldClass = BareField

                params = {
                    'column_name': column_name,
                    'null': column.nullable}
                if column.primary_key and composite_key:
                    if FieldClass is AutoField:
                        FieldClass = IntegerField
                    params['primary_key'] = False
                elif column.primary_key and FieldClass is not AutoField:
                    params['primary_key'] = True
                if column.is_foreign_key():
                    if column.is_self_referential_fk():
                        params['model'] = 'self'
                    else:
                        dest_table = column.foreign_key.dest_table
                        if dest_table in models:
                            params['model'] = models[dest_table]
                        else:
                            FieldClass = DeferredForeignKey
                            params['rel_model_name'] = dest_table
                    if column.to_field:
                        params['field'] = column.to_field

                    # Generate a unique related name.
                    params['backref'] = '%s_DEL' % table  # DEL suffix is added and will be removed soon

                if column.default is not None:
                    constraint = SQL('DEFAULT %s' % column.default)
                    params['constraints'] = [constraint]

                if column_name in column_indexes and not \
                   column.is_primary_key():
                    if column_indexes[column_name]:
                        params['unique'] = True
                    elif not column.is_foreign_key():
                        params['index'] = True

                attrs[column.name] = FieldClass(**params)

            try:
                models[table] = type(str(table), (BaseModel,), attrs)
            except ValueError:
                if not skip_invalid:
                    raise
            finally:
                if table in pending:
                    pending.remove(table)

        for table, model in sorted(database.model_names.items()):
            if table not in models:
                _create_model(table, models)

        for name, model in models.items():
            attrs = {}
            for fk in model._meta.backrefs.keys():
                if 'id' not in fk.model._meta.fields:
                    right_model = [m for m in fk.model._meta.model_refs.keys() if m != model]
                    if len(right_model) != 1:
                        raise ValueError('the Many-to-many model %s contains more than 2 foreign keys' % fk.model)
                    right_model = right_model[0]
                    attrs[pluralize(right_model._meta.name)] = fk
                else:
                    attrs[pluralize(fk.model._meta.name)] = fk
            for k in set(attrs.keys()).copy():
                if 'DEL' in k:
                    attrs.pop(k)
            for attr_name, attr in attrs.items():
                setattr(model, attr_name, attr)

        return models


def generate_models(database, schema=None, **options):
    introspector = PatchedIntrospector.from_database(database, schema=schema)
    return introspector.generate_models(**options)
