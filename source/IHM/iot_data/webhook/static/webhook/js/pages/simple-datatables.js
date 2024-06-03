
let dataTable = new simpleDatatables.DataTable(document.getElementById("table1"), {
            // Utiliser le fichier de localisation depuis votre projet Django
            labels : {
                          "placeholder": "Rechercher...",
                          "perPage": "Afficher {select} éléments",
                          "noRows": "Aucune entrée trouvée",
                          "info": "Affichage de {start} à {end} sur {rows} éléments "
                      },
        });
console.log(dataTable);

// Move "per page dropdown" selector element out of label
// to make it work with bootstrap 5. Add bs5 classes.
function adaptPageDropdown() {
  const selector = dataTable.wrapper.querySelector(".dataTable-selector");
  selector.parentNode.parentNode.insertBefore(selector, selector.parentNode);
  selector.classList.add("form-select");
}

// Add bs5 classes to pagination elements
function adaptPagination() {
  const paginations = dataTable.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list"
  );

  for (const pagination of paginations) {
    pagination.classList.add(...["pagination", "pagination-primary"]);
  }

  const paginationLis = dataTable.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li"
  );

  for (const paginationLi of paginationLis) {
    paginationLi.classList.add("page-item");
  }

  const paginationLinks = dataTable.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li a"
  );

  for (const paginationLink of paginationLinks) {
    paginationLink.classList.add("page-link");
  }
}

/*// Patch "per page dropdown" and pagination after table rendered
dataTable.on("datatable.init", function () {
    adaptPageDropdown();
    adaptPagination();
});*/

// Re-patch pagination after the page was changed
dataTable.on("datatable.page", adaptPagination);




let dataTable2 = new simpleDatatables.DataTable(document.getElementById("table2"), {
            // Utiliser le fichier de localisation depuis votre projet Django
            labels : {
                          "placeholder": "Rechercher...",
                          "perPage": "Afficher {select} éléments",
                          "noRows": "Aucune entrée trouvée",
                          "info": "Affichage de {start} à {end} sur {rows} éléments "
                      },
        });

// Move "per page dropdown" selector element out of label
// to make it work with bootstrap 5. Add bs5 classes.
function adaptPageDropdown() {
  const selector = dataTable2.wrapper.querySelector(".dataTable-selector");
  selector.parentNode.parentNode.insertBefore(selector, selector.parentNode);
  selector.classList.add("form-select");
}

// Add bs5 classes to pagination elements
function adaptPagination() {
  const paginations = dataTable2.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list"
  );

  for (const pagination of paginations) {
    pagination.classList.add(...["pagination", "pagination-primary"]);
  }

  const paginationLis = dataTable2.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li"
  );

  for (const paginationLi of paginationLis) {
    paginationLi.classList.add("page-item");
  }

  const paginationLinks = dataTable2.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li a"
  );

  for (const paginationLink of paginationLinks) {
    paginationLink.classList.add("page-link");
  }
}

/*// Patch "per page dropdown" and pagination after table rendered
dataTable2.on("datatable.init", function () {
    adaptPageDropdown();
    adaptPagination();
});*/

// Re-patch pagination after the page was changed
dataTable2.on("datatable.page", adaptPagination);






let dataTable3 = new simpleDatatables.DataTable(document.getElementById("table3"), {
            // Utiliser le fichier de localisation depuis votre projet Django
            labels : {
                          "placeholder": "Rechercher...",
                          "perPage": "Afficher {select} éléments",
                          "noRows": "Aucune entrée trouvée",
                          "info": "Affichage de {start} à {end} sur {rows} éléments "
                      },
        });

// Move "per page dropdown" selector element out of label
// to make it work with bootstrap 5. Add bs5 classes.
function adaptPageDropdown() {
  const selector = dataTable3.wrapper.querySelector(".dataTable-selector");
  selector.parentNode.parentNode.insertBefore(selector, selector.parentNode);
  selector.classList.add("form-select");
}

// Add bs5 classes to pagination elements
function adaptPagination() {
  const paginations = dataTable3.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list"
  );

  for (const pagination of paginations) {
    pagination.classList.add(...["pagination", "pagination-primary"]);
  }

  const paginationLis = dataTable3.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li"
  );

  for (const paginationLi of paginationLis) {
    paginationLi.classList.add("page-item");
  }

  const paginationLinks = dataTable3.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li a"
  );

  for (const paginationLink of paginationLinks) {
    paginationLink.classList.add("page-link");
  }
}

/*// Patch "per page dropdown" and pagination after table rendered
dataTable3.on("datatable.init", function () {
    adaptPageDropdown();
    adaptPagination();
});*/

// Re-patch pagination after the page was changed
dataTable3.on("datatable.page", adaptPagination);



let dataTable4 = new simpleDatatables.DataTable(document.getElementById("table4"), {
            // Utiliser le fichier de localisation depuis votre projet Django
            labels : {
                          "placeholder": "Rechercher...",
                          "perPage": "Afficher {select} éléments",
                          "noRows": "Aucune entrée trouvée",
                          "info": "Affichage de {start} à {end} sur {rows} éléments "
                      },
        });

// Move "per page dropdown" selector element out of label
// to make it work with bootstrap 5. Add bs5 classes.
function adaptPageDropdown() {
  const selector = dataTable4.wrapper.querySelector(".dataTable-selector");
  selector.parentNode.parentNode.insertBefore(selector, selector.parentNode);
  selector.classList.add("form-select");
}

// Add bs5 classes to pagination elements
function adaptPagination() {
  const paginations = dataTable4.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list"
  );

  for (const pagination of paginations) {
    pagination.classList.add(...["pagination", "pagination-primary"]);
  }

  const paginationLis = dataTable4.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li"
  );

  for (const paginationLi of paginationLis) {
    paginationLi.classList.add("page-item");
  }

  const paginationLinks = dataTable4.wrapper.querySelectorAll(
    "ul.dataTable-pagination-list li a"
  );

  for (const paginationLink of paginationLinks) {
    paginationLink.classList.add("page-link");
  }
}

/*// Patch "per page dropdown" and pagination after table rendered
dataTable4.on("datatable.init", function () {
    adaptPageDropdown();
    adaptPagination();
});*/

// Re-patch pagination after the page was changed
dataTable4.on("datatable.page", adaptPagination);