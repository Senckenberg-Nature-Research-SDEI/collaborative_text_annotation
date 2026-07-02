# Competency Questions and SPARQL Queries

## CQ1. Taxonomic Synonymy

**Question:** Which taxonomic names are recorded as subjective junior synonyms of a given taxon, and what is their accepted name?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>
PREFIX dwc: <http://rs.tdwg.org/dwc/terms/>

SELECT ?synonym ?acceptedName
WHERE {
    ?synonym ex:subjectiveJuniorSynonymOf ?acceptedTaxon .
    ?acceptedTaxon dwc:scientificName ?acceptedName .

    FILTER(?acceptedTaxon = <TARGET_TAXON_URI>)
}
```

---

## CQ2. Type Specimen Repository

**Question:** Which preserved specimen represents the type of a given taxon, and in which institution or collection is it currently deposited?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?specimen ?collection
WHERE {
    ?specimen ex:typeForTaxon <TARGET_TAXON_URI> ;
              ex:institutionCode ?collection .
}
```

---

## CQ3. Associated Digital Resources

**Question:** What digital resources (e.g., photographs, nucleotide sequences, or other related resources) are associated with a given preserved specimen?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?resource ?type
WHERE {
    <TARGET_SPECIMEN_URI> ex:hasAssociatedResource ?resource .
    OPTIONAL { ?resource a ?type . }
}
```

---

## CQ4. Temporal Trends in Species Descriptions

**Question:** How many taxa were described during each year?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?year (COUNT(?taxon) AS ?speciesCount)
WHERE {
    ?taxon ex:yearPublished ?year .
}
GROUP BY ?year
ORDER BY ?year
```

---

## CQ5. Type Locality Information

**Question:** At which collecting event and geographic location was the occurrence corresponding to a type specimen recorded?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?event ?location
WHERE {
    <TARGET_SPECIMEN_URI> ex:hasOccurrence ?occurrence .
    ?occurrence ex:recordedAtEvent ?event ;
                ex:atLocation ?location .
}
```

---

## CQ6. Geographic Distribution of Type Specimens

**Question:** Which preserved specimens have occurrences recorded within a specified geographic region?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?specimen
WHERE {
    ?specimen ex:hasOccurrence ?occurrence .
    ?occurrence ex:atLocation ?location .
    ?location ex:withinRegion <TARGET_REGION_URI> .
}
```

---

## CQ7. Taxonomic Authorship

**Question:** Who established a given taxon, and which publication documents its original description?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT ?author ?publication
WHERE {
    <TARGET_TAXON_URI> ex:authoredBy ?author ;
                       ex:publishedIn ?publication .
}
```

---

## CQ8. Collection Holdings

**Question:** Which preserved specimens are held by a specified institution?

```sparql
PREFIX ex: <http://specimenkb.sdei.senckenberg.de/ontology#>

SELECT ?specimen
WHERE {
    ?specimen ex:institutionCode <TARGET_INSTITUTION_URI> .
}
```