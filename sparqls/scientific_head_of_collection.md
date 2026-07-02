# Competency Questions and SPARQL Queries

## CQ1. Type Specimen Inventory

```sparql
SELECT ?specimen ?catalogNumber ?scientificName ?typeStatus
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?specimen dwc:catalogNumber ?catalogNumber . }
  OPTIONAL { ?specimen dwc:scientificName ?scientificName . }
  OPTIONAL { ?specimen dwc:typeStatus ?typeStatus . }
}
ORDER BY ?scientificName
```

---

## CQ2. Type Specimen Quantification

```sparql
SELECT (COUNT(DISTINCT ?specimen) AS ?numberOfTypeSpecimens)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> .
}
```

---

## CQ3. Taxonomic Distribution

```sparql
SELECT ?family ?genus
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?specimen dwc:family ?family . }
  OPTIONAL { ?specimen dwc:genus ?genus . }
}
GROUP BY ?family ?genus
ORDER BY DESC(?specimenCount)
```

---

## CQ4. Collection Strengths by Taxon

```sparql
SELECT ?family
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> ;
            dwc:family ?family .
}
GROUP BY ?family
ORDER BY DESC(?specimenCount)
LIMIT 10
```

---

## CQ5. Geographic Coverage

```sparql
SELECT ?country ?stateProvince
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?specimen dwc:country ?country . }
  OPTIONAL { ?specimen dwc:stateProvince ?stateProvince . }
}
GROUP BY ?country ?stateProvince
ORDER BY DESC(?specimenCount)
```

---

## CQ6. Published Catalogues

```sparql
SELECT DISTINCT ?catalogue ?title ?year
WHERE {
  ?catalogue ex:documentsCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?catalogue dcterms:title ?title . }

  OPTIONAL {
    ?catalogue dcterms:issued ?date .
    BIND(YEAR(?date) AS ?year)
  }
}
ORDER BY ?year
```

---

## CQ7. Specialist Contributions

```sparql
SELECT ?author
       (COUNT(DISTINCT ?publication) AS ?publicationCount)
WHERE {
  ?publication ex:documentsCollection <TARGET_COLLECTION_URI> ;
               dcterms:creator ?author .
}
GROUP BY ?author
ORDER BY DESC(?publicationCount)
```

---

## CQ8. Historical Interpretation

```sparql
SELECT ?publication ?title ?year
WHERE {
  ?publication ex:documentsCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?publication dcterms:title ?title . }

  OPTIONAL {
    ?publication dcterms:issued ?date .
    BIND(YEAR(?date) AS ?year)
  }
}
ORDER BY ?year
```

---

## CQ9. Collection Development

```sparql
SELECT ?year
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> ;
            dwc:eventDate ?date .

  BIND(YEAR(?date) AS ?year)
}
GROUP BY ?year
ORDER BY ?year
```

---

## CQ10. Collection Strength Assessment

```sparql
SELECT ?family
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
       (COUNT(DISTINCT ?publication) AS ?publicationCount)
WHERE {
  ?specimen a ex:TypeSpecimen ;
            ex:belongsToCollection <TARGET_COLLECTION_URI> ;
            dwc:family ?family .

  OPTIONAL {
    ?publication ex:documentsTypeSpecimen ?specimen .
  }
}
GROUP BY ?family
ORDER BY DESC(?specimenCount) DESC(?publicationCount)
```

---

## CQ11. Knowledge Contribution of Catalogues

```sparql
SELECT ?catalogue ?title
       (COUNT(DISTINCT ?specimen) AS ?documentedSpecimens)
WHERE {
  ?catalogue ex:documentsTypeSpecimen ?specimen .

  ?specimen ex:belongsToCollection <TARGET_COLLECTION_URI> .

  OPTIONAL { ?catalogue dcterms:title ?title . }
}
GROUP BY ?catalogue ?title
ORDER BY DESC(?documentedSpecimens)
```