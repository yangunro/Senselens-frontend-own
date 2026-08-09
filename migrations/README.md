# Database migrations

Migrations in this directory are reviewed SQL changes. The FastAPI
application does not execute them automatically.

## `001_add_route_geometry.sql`

This adds the encoded Google route geometry, navigation steps, and creation
time required for durable generated routes.

Before applying it:

1. Confirm the shared Supabase project and target environment with the
   database owner.
2. Take a schema backup or confirm point-in-time recovery is available.
3. Run the migration in a non-production environment first.
4. Verify existing rows and API queries.
5. Only then run it through the Supabase SQL editor or the team's migration
   process.

After the migration is approved and applied, the next implementation is a
route repository that writes generated routes and their sensory scores in a
single database transaction.
