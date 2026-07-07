let pagePermission = [1, 2, 3];

if (!pagePermission.includes(LOCAL_VARIABLES.Authorization.UserType)) {
    noPermission();
}

let mapContainerID = "mapContainer";
mapMonitor(mapContainerID);