// Read-only log list; the shared Tabulator engine (project.js) auto-initialises
// the table from its cfg-ajax-url, so there is no form/CRUD wiring here.
let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}
