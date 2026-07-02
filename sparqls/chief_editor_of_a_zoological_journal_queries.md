# Competency Questions and SPARQL Queries

## CQ1. Published Type Specimens and Metadata

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?specimen ?institution ?institutionCode ?catalogNumber ?taxon
       ?locality ?sex ?individualCount ?publication
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen ex:heldBy ?institution . }
  OPTIONAL { ?specimen dwc:institutionCode ?institutionCode . }
  OPTIONAL { ?specimen dwc:catalogNumber ?catalogNumber . }
  OPTIONAL { ?specimen dwc:scientificName ?taxon . }
  OPTIONAL { ?specimen dwc:locality ?locality . }
  OPTIONAL { ?specimen dwc:sex ?sex . }
  OPTIONAL { ?specimen dwc:individualCount ?individualCount . }
}
```

## CQ2. Type Specimen Quantification

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT (COUNT(DISTINCT ?specimen) AS ?typeSpecimenCount)
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .
}
```

## CQ3. Collection and Repository Holdings

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT DISTINCT ?institution ?collection
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen ex:heldBy ?institution . }
  OPTIONAL { ?specimen dwc:collectionCode ?collection . }
}
ORDER BY ?institution ?collection
```

## CQ4. Taxonomic Distribution

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?family ?genus ?species (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen dwc:family ?family . }
  OPTIONAL { ?specimen dwc:genus ?genus . }
  OPTIONAL { ?specimen dwc:specificEpithet ?species . }
}
GROUP BY ?family ?genus ?species
ORDER BY DESC(?specimenCount)
```

## CQ5. Geographic Distribution

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?country ?stateProvince ?locality (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen dwc:country ?country . }
  OPTIONAL { ?specimen dwc:stateProvince ?stateProvince . }
  OPTIONAL { ?specimen dwc:locality ?locality . }
}
GROUP BY ?country ?stateProvince ?locality
ORDER BY DESC(?specimenCount)
```

## CQ6. Relevant Publications and Catalogues

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?publication ?title ?isCatalogue
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?publication dcterms:title ?title . }

  BIND(EXISTS {
    ?publication a ex:TypeSpecimenCatalogue .
  } AS ?isCatalogue)
}
GROUP BY ?publication ?title ?isCatalogue
ORDER BY ?title
```

## CQ7. Publication Context

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?publication ?title ?section
WHERE {
  ?publication ex:mentionsTypeSpecimen <TARGET_SPECIMEN_URI> .

  OPTIONAL { ?publication dcterms:title ?title . }
  OPTIONAL {
    ?publication ex:hasSection ?section .
    ?section ex:mentionsTypeSpecimen <TARGET_SPECIMEN_URI> .
  }
}
```

## CQ8. Major Contributors

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?publication ?title (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen .

  OPTIONAL { ?publication dcterms:title ?title . }
}
GROUP BY ?publication ?title
ORDER BY DESC(?specimenCount)
```

## CQ9. Temporal Trends

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?year (COUNT(DISTINCT ?specimen) AS ?specimenCount)
WHERE {
  ?publication ex:mentionsTypeSpecimen ?specimen ;
               dcterms:issued ?date .

  BIND(YEAR(?date) AS ?year)
}
GROUP BY ?year
ORDER BY ?year
```