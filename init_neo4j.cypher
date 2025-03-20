LOAD CSV WITH HEADERS FROM 'file:///Dataset_B.csv' AS row
CREATE (:Lenguaje { 
    id: toInteger(row.id), 
    nombre: row.nombre, 
    popularidad: toInteger(row.popularidad), 
    velocidad: toInteger(row.velocidad), 
    paradigma: row.paradigma, 
    anio_creacion: toInteger(row.anio_creacion)
});
