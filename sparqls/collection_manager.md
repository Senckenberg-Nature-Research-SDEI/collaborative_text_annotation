# Competency Questions and SPARQL Queries

## CQ1. Type Specimen Documentation

```sparql
SELECT ?specimen ?publication ?title ?taxon ?institution ?locality ?identifier
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?publication dcterms:title ?title . }
  OPTIONAL { ?specimen dwc:scientificName ?taxon . }
  OPTIONAL { ?specimen ex:heldBy ?institution . }
  OPTIONAL { ?specimen dwc:locality ?locality . }
  OPTIONAL { ?specimen dcterms:identifier ?identifier . }
}
```

## CQ2. Available Catalogues and Publications

```sparql
SELECT DISTINCT ?publication ?title
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .
  ?specimen ex:heldBy <TARGET_INSTITUTION_OR_COLLECTION_URI> .

  OPTIONAL { ?publication dcterms:title ?title . }
}
ORDER BY ?title
```

## CQ3. Specialist Contributions

```sparql
SELECT DISTINCT ?author ?publication ?title
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen ;
               dcterms:creator ?author .

  ?specimen ex:heldBy <TARGET_COLLECTION_URI> .

  OPTIONAL { ?publication dcterms:title ?title . }
}
ORDER BY ?author ?title
```

## CQ4. Relevant Publications

```sparql
SELECT DISTINCT ?publication ?title
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?publication dcterms:title ?title . }

  FILTER(
    ?specimen = <TARGET_SPECIMEN_URI>
    || EXISTS { ?specimen dwc:genus <TARGET_GENUS> }
    || EXISTS { ?specimen dwc:family <TARGET_FAMILY> }
  )
}
```

## CQ5. Metadata Availability

```sparql
SELECT ?specimen
       (BOUND(?taxon) AS ?hasTaxonomy)
       (BOUND(?locality) AS ?hasLocality)
       (BOUND(?collector) AS ?hasCollector)
       (BOUND(?identifier) AS ?hasIdentifier)
       (BOUND(?repository) AS ?hasRepository)
       (BOUND(?reference) AS ?hasReference)
       (BOUND(?image) AS ?hasImage)
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen dwc:scientificName ?taxon . }
  OPTIONAL { ?specimen dwc:locality ?locality . }
  OPTIONAL { ?specimen dwc:recordedBy ?collector . }
  OPTIONAL { ?specimen dcterms:identifier ?identifier . }
  OPTIONAL { ?specimen ex:heldBy ?repository . }
  OPTIONAL { ?publication dcterms:bibliographicCitation ?reference . }
  OPTIONAL { ?specimen foaf:depiction ?image . }
}
```

## CQ6. Documentation Completeness

```sparql
SELECT ?specimen (COUNT(DISTINCT ?metadataValue) AS ?metadataCount)
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  {
    ?specimen dwc:scientificName ?metadataValue .
  }
  UNION {
    ?specimen dwc:locality ?metadataValue .
  }
  UNION {
    ?specimen dwc:recordedBy ?metadataValue .
  }
  UNION {
    ?specimen dcterms:identifier ?metadataValue .
  }
  UNION {
    ?specimen ex:heldBy ?metadataValue .
  }
  UNION {
    ?specimen foaf:depiction ?metadataValue .
  }
  UNION {
    ?publication dcterms:bibliographicCitation ?metadataValue .
  }
}
GROUP BY ?specimen
ORDER BY DESC(?metadataCount)
```

## CQ7. Catalogue Coverage

```sparql
SELECT ?catalogue ?title
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
       (COUNT(DISTINCT ?metadataValue) AS ?metadataCount)
WHERE {
  ?catalogue a ex:TypeSpecimenCatalogue ;
             ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?catalogue dcterms:title ?title . }

  FILTER EXISTS {
    ?specimen ex:heldBy <TARGET_COLLECTION_URI> .
  }

  OPTIONAL {
    {
      ?specimen dwc:scientificName ?metadataValue .
    }
    UNION {
      ?specimen dwc:locality ?metadataValue .
    }
    UNION {
      ?specimen dcterms:identifier ?metadataValue .
    }
    UNION {
      ?specimen ex:heldBy ?metadataValue .
    }
  }
}
GROUP BY ?catalogue ?title
ORDER BY DESC(?specimenCount) DESC(?metadataCount)
```

## CQ8. Multiple Documentation Sources

```sparql
SELECT ?specimen (COUNT(DISTINCT ?publication) AS ?sourceCount)
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .
}
GROUP BY ?specimen
HAVING (COUNT(DISTINCT ?publication) > 1)
ORDER BY DESC(?sourceCount)
```

## CQ9. Historical Changes in Documentation

```sparql
SELECT ?specimen ?publication ?title ?date ?property ?value
WHERE {
  ?publication ex:documentsTypeSpecimen <TARGET_SPECIMEN_URI> ;
               dcterms:issued ?date .

  OPTIONAL { ?publication dcterms:title ?title . }

  <TARGET_SPECIMEN_URI> ?property ?value .
}
ORDER BY ?date
```

## CQ10. Identifiers and External Resources

```sparql
SELECT ?specimen ?identifier ?catalogNumber ?externalResource
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?specimen dcterms:identifier ?identifier . }
  OPTIONAL { ?specimen dwc:catalogNumber ?catalogNumber . }
  OPTIONAL { ?specimen rdfs:seeAlso ?externalResource . }
}
```

## CQ11. Richly Connected Specimens

```sparql
SELECT ?specimen (COUNT(DISTINCT ?linkedEntity) AS ?connectionCount)
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  {
    ?specimen ?property ?linkedEntity .
  }
  UNION {
    ?linkedEntity ?property ?specimen .
  }
}
GROUP BY ?specimen
ORDER BY DESC(?connectionCount)
```

## CQ12. Information Diversity and Coverage

```sparql
SELECT ?publication ?title
       (COUNT(DISTINCT ?specimen) AS ?specimenCount)
       (COUNT(DISTINCT ?property) AS ?metadataPropertyCount)
       (COUNT(DISTINCT ?value) AS ?metadataValueCount)
WHERE {
  ?publication ex:documentsTypeSpecimen ?specimen .

  OPTIONAL { ?publication dcterms:title ?title . }

  OPTIONAL {
    ?specimen ?property ?value .
  }
}
GROUP BY ?publication ?title
ORDER BY DESC(?metadataPropertyCount) DESC(?metadataValueCount)
```