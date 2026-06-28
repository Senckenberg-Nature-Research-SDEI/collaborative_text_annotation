#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="${1:-data/competency_questions/competency_questions.json}"
OUTPUT_FILE="${2:-outputs/cq_concepts_properties.jsonl}"
GROUPED_OUTPUT_FILE="${3:-outputs/cq_concepts_properties_grouped.json}"
RDF_OUTPUT_FILE="${4:-outputs/cq_concepts_properties.ttl}"
MODEL_ALIAS="${MODEL_ALIAS:-llm_model}"
CONFIG_FILE="${CONFIG_FILE:-config/model_config.yaml}"
TERM_VERSIONS_FILE="${TERM_VERSIONS_FILE:-data/existing_ontologies/term_versions.csv}"

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Input file not found: $INPUT_FILE"
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_FILE")"
mkdir -p "$(dirname "$GROUPED_OUTPUT_FILE")"
mkdir -p "$(dirname "$RDF_OUTPUT_FILE")"
TMP_PROMPTS_FILE="$(mktemp)"
SYSTEM_PROMPT_FILE="$(mktemp)"
DWC_CONTEXT_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_PROMPTS_FILE" "$SYSTEM_PROMPT_FILE" "$DWC_CONTEXT_FILE"
}
trap cleanup EXIT

if [[ ! -f "$TERM_VERSIONS_FILE" ]]; then
  echo "Term versions file not found: $TERM_VERSIONS_FILE"
  exit 1
fi

python - <<'PY' "$TERM_VERSIONS_FILE" "$DWC_CONTEXT_FILE"
import csv
import sys

term_versions_path, output_path = sys.argv[1], sys.argv[2]

class_rows = []
property_rows = []

with open(term_versions_path, "r", encoding="utf-8") as handle:
  for row in csv.DictReader(handle):
    term_iri = (row.get("term_iri") or "").strip()
    rdf_type = (row.get("rdf_type") or "").strip()
    status = (row.get("status") or "").strip().lower()
    label = (row.get("label") or "").strip()
    local_name = (row.get("term_localName") or "").strip()

    if status != "recommended" or not term_iri.startswith("http://rs.tdwg.org/dwc/"):
      continue

    entry = f"{label} [{local_name}]"
    if "Class" in rdf_type:
      class_rows.append(entry)
    elif "Property" in rdf_type:
      property_rows.append(entry)

priority_classes = [
  "Taxon [Taxon]",
  "Occurrence [Occurrence]",
  "Organism [Organism]",
  "MaterialEntity [MaterialEntity]",
  "MaterialCitation [MaterialCitation]",
  "Identification [Identification]",
  "Event [Event]",
  "Location [Location]",
  "GeologicalContext [GeologicalContext]",
]

priority_properties = [
  "collectionCode [collectionCode]",
  "institutionCode [institutionCode]",
  "catalogNumber [catalogNumber]",
  "occurrenceID [occurrenceID]",
  "basisOfRecord [basisOfRecord]",
  "scientificName [scientificName]",
  "acceptedNameUsage [acceptedNameUsage]",
  "taxonomicStatus [taxonomicStatus]",
  "recordedBy [recordedBy]",
  "identifiedBy [identifiedBy]",
  "eventDate [eventDate]",
  "decimalLatitude [decimalLatitude]",
  "decimalLongitude [decimalLongitude]",
  "locality [locality]",
  "verbatimLocality [verbatimLocality]",
  "verbatimCoordinates [verbatimCoordinates]",
  "verbatimLatitude [verbatimLatitude]",
  "verbatimLongitude [verbatimLongitude]",
  "verbatimSRS [verbatimSRS]",
  "higherGeography [higherGeography]",
  "higherGeographyID [higherGeographyID]",
  "eventID [eventID]",
  "fieldNumber [fieldNumber]",
  "locationID [locationID]",
  "datasetID [datasetID]",
  "institutionID [institutionID]",
  "ownerInstitutionCode [ownerInstitutionCode]",
  "associatedMedia [associatedMedia]",
  "associatedReferences [associatedReferences]",
  "references [references]",
  "bibliographicCitation [bibliographicCitation]",
  "type [type]",
]

selected_classes = priority_classes + [entry for entry in class_rows if entry not in priority_classes][:20]
selected_properties = priority_properties + [entry for entry in property_rows if entry not in priority_properties][:30]

with open(output_path, "w", encoding="utf-8") as handle:
  handle.write("DWC Context for extraction\n")
  handle.write("Use these current Darwin Core terms when they fit the question. Prefer exact labels and current recommended terms over invented or generic labels.\n")
  handle.write("\nCurrent DWC classes:\n")
  for entry in selected_classes:
    handle.write(f"- {entry}\n")
  handle.write("\nCurrent DWC properties:\n")
  for entry in selected_properties:
    handle.write(f"- {entry}\n")
PY

cat > "$SYSTEM_PROMPT_FILE" <<'EOF'
You are an ontology engineering assistant for biodiversity collection management.
Extract candidate ontology concepts (classes) and properties from each competency question.

IMPORTANT: Use current recommended Darwin Core (DWC) terms whenever a term fits the question.
Map concepts to DWC classes and properties to DWC properties listed below.
Do NOT invent generic replacements if a DWC term exists. Do NOT use superseded or deprecated terms.

=== CURRENT DWC CLASSES (use these as concept labels and domain/range values) ===
Taxon                — A group of organisms considered to be taxonomically homogeneous
Occurrence           — A dwc:Event that establishes the state of a dwc:Organism at a place and time
MaterialEntity       — An entity that can be identified and consists in whole or part of physical matter
MaterialCitation     — A reference to or citation of one or more specimens in scholarly publications
MaterialSample       — A material entity that represents an entity of interest in whole or in part
PreservedSpecimen    — A specimen that has been preserved
FossilSpecimen       — A preserved specimen that is a fossil
LivingSpecimen       — A specimen that is alive
HumanObservation     — An output of a human observation process
MachineObservation   — An output of a machine observation process
Identification       — A classification of a resource according to a classification scheme
Organism             — A particular organism or defined group of organisms
OrganismInteraction  — An interaction between two Organisms during an Event
Event                — An action or set of circumstances occurring at a Location during a period of time
ResourceRelationship — A relationship of one resource to another
MeasurementOrFact    — A measurement of or fact about a resource
Assertion            — A statement about a resource
NucleotideSequence   — A digital representation of a nucleotide sequence
NucleotideAnalysis   — A link between a NucleotideSequence or Identification and an Event
MolecularProtocol    — A protocol used to perform a NucleotideAnalysis
Protocol             — A method used during an action
Provenance           — Information about an entity's origins
GeologicalContext    — Geological designations (stratigraphy etc.) that qualify a Location
UsagePolicy          — Rights, usage, and attribution statements applicable to an entity

=== CURRENT DWC PROPERTIES (use these as property labels) ===
--- Record-level ---
basisOfRecord, institutionCode, collectionCode, institutionID, collectionID,
ownerInstitutionCode, datasetID, datasetName, informationWithheld, dataGeneralizations,
dynamicProperties, feedbackURL

--- Occurrence ---
occurrenceID, catalogNumber, recordNumber, recordedBy, recordedByID,
individualCount, organismQuantity, organismQuantityType, sex, lifeStage,
reproductiveCondition, caste, behavior, vitality, establishmentMeans,
degreeOfEstablishment, pathway, georeferenceVerificationStatus, occurrenceStatus,
associatedMedia, associatedOccurrences, associatedOrganisms, associatedReferences,
associatedTaxa, occurrenceRemarks

--- Organism ---
organismID, organismName, organismScope, associatedOrganisms, previousIdentifications,
organismRemarks

--- MaterialEntity ---
materialEntityID, preparations, disposition, verbatimLabel, associatedSequences,
materialEntityRemarks

--- Event ---
eventID, parentEventID, eventCategory, eventType, fieldNumber, eventDate, eventTime,
startDayOfYear, endDayOfYear, year, month, day, verbatimEventDate,
habitat, fieldNotes, eventRemarks, samplingProtocol, sampleSizeValue, sampleSizeUnit,
samplingEffort, eventDuration, eventDurationUnit

--- Location ---
locationID, higherGeographyID, higherGeography, continent, waterBody, islandGroup,
island, country, countryCode, stateProvince, county, municipality, locality,
verbatimLocality, verbatimElevation, verticalDatum, verbatimDepth,
verbatimCoordinates, verbatimLatitude, verbatimLongitude, verbatimCoordinateSystem,
verbatimSRS, decimalLatitude, decimalLongitude, geodeticDatum,
coordinateUncertaintyInMeters, coordinatePrecision, pointRadiusSpatialFit,
footprintWKT, footprintSRS, footprintSpatialFit, georeferencedBy, georeferencedDate,
georeferenceProtocol, georeferenceSources, georeferenceRemarks, locationRemarks,
minimumElevationInMeters, maximumElevationInMeters, minimumDepthInMeters, maximumDepthInMeters

--- GeologicalContext ---
geologicalContextID, earliestEonOrLowestEonothem, latestEonOrHighestEonothem,
earliestEraOrLowestErathem, latestEraOrHighestErathem,
earliestPeriodOrLowestSystem, latestPeriodOrHighestSystem,
earliestEpochOrLowestSeries, latestEpochOrHighestSeries,
earliestAgeOrLowestStage, latestAgeOrHighestStage, lowestBiostratigraphicZone,
highestBiostratigraphicZone, lithostratigraphicTerms, group, formation, member, bed

--- Identification ---
identificationID, verbatimIdentification, identificationQualifier, typeStatus,
identifiedBy, identifiedByID, dateIdentified, identificationReferences,
identificationVerificationStatus, identificationRemarks

--- Taxon ---
taxonID, scientificNameID, acceptedNameUsageID, parentNameUsageID, originalNameUsageID,
nameAccordingToID, namePublishedInID, taxonConceptID, scientificName,
acceptedNameUsage, parentNameUsage, originalNameUsage, nameAccordingTo, namePublishedIn,
namePublishedInYear, higherClassification, kingdom, phylum, class, order, family,
subfamily, tribe, subtribe, genus, genericName, subgenus, infragenericEpithet,
specificEpithet, infraspecificEpithet, cultivarEpithet, taxonRank,
verbatimTaxonRank, scientificNameAuthorship, vernacularName, nomenclaturalCode,
taxonomicStatus, nomenclaturalStatus, taxonRemarks

--- MaterialCitation ---
bibliographicCitation, occurrenceID, typeStatus, verbatimLabel

--- MeasurementOrFact ---
measurementID, measurementType, measurementValue, measurementAccuracy,
measurementUnit, measurementDeterminedBy, measurementDeterminedDate, measurementRemarks

--- Agent / Provenance / Relationship ---
agentID, agentType, agentRemarks, agentRoleOrder
provenanceID, provenanceType, provenance
relationshipID, relationshipOfResource, relationshipAccordingTo,
relationshipEstablishedDate, relationshipRemarks

Return one strict JSON object with this shape:
{
  "user_story": "string",
  "cq_id": "string",
  "cq_title": "string",
  "question": "string",
  "concepts": [
    {
      "label": "string — use a DWC class name from the list above when it fits",
      "description": "short definition",
      "synonyms": ["string"]
    }
  ],
  "properties": [
    {
      "label": "string — use a DWC property name from the list above when it fits",
      "domain": "string — DWC class name",
      "range": "string — DWC class name or xsd datatype (e.g. xsd:string, xsd:date)",
      "description": "short definition"
    }
  ]
}
Rules:
- Prefer exact DWC class or property names over paraphrases.
- domain and range should be DWC class names from the class list above wherever possible.
- Keep labels concise and singular.
- Use only information implied by the question.
- If uncertain, leave a shorter list instead of inventing details.
EOF

python - <<'PY' "$INPUT_FILE" "$TMP_PROMPTS_FILE" "$DWC_CONTEXT_FILE"
import json
import sys

input_path, output_path, dwc_context_path = sys.argv[1], sys.argv[2], sys.argv[3]


with open(dwc_context_path, "r", encoding="utf-8") as handle:
  dwc_context = handle.read().strip()

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

prompts = []
for item in data:
    story = item.get("user_story", {})
    story_title = story.get("title", "")
    for cq in story.get("competency_questions", []):
        cq_id = cq.get("id", "")
        cq_title = cq.get("title", "")
        question = cq.get("question", "")
        prompt = (
            f"User Story: {story_title}\n"
            f"CQ ID: {cq_id}\n"
            f"CQ Title: {cq_title}\n"
            f"Question: {question}\n"
            f"{dwc_context}\n"
            "Task: Extract candidate ontology concepts and properties, preferring Darwin Core terms for concepts, properties, domain, and range where applicable."
        )
        prompts.append(prompt)

with open(output_path, "w", encoding="utf-8") as out:
    for prompt in prompts:
        out.write(json.dumps({"prompt": prompt}, ensure_ascii=False) + "\n")
PY

python run_prompts.py \
  --config "$CONFIG_FILE" \
  --model-alias "$MODEL_ALIAS" \
  --system-prompt "$(cat "$SYSTEM_PROMPT_FILE")" \
  --prompt-file "$TMP_PROMPTS_FILE" \
  --output "$OUTPUT_FILE"

python - <<'PY' "$OUTPUT_FILE" "$GROUPED_OUTPUT_FILE"
import json
import re
import sys
from collections import OrderedDict

jsonl_path, grouped_path = sys.argv[1], sys.argv[2]


def parse_response_payload(text):
  text = (text or "").strip()
  if not text:
    return None

  if text.startswith("```"):
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)

  try:
    return json.loads(text)
  except json.JSONDecodeError:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
      candidate = text[start : end + 1]
      try:
        return json.loads(candidate)
      except json.JSONDecodeError:
        return None
    return None


grouped = OrderedDict()
invalid_rows = []

with open(jsonl_path, "r", encoding="utf-8") as f:
  for line_no, line in enumerate(f, start=1):
    line = line.strip()
    if not line:
      continue

    row = json.loads(line)
    payload = parse_response_payload(row.get("response", ""))
    if payload is None:
      invalid_rows.append(line_no)
      continue

    user_story = payload.get("user_story", "UNKNOWN")
    cq_id = payload.get("cq_id", "UNKNOWN")

    if user_story not in grouped:
      grouped[user_story] = OrderedDict()

    grouped[user_story][cq_id] = payload

result = {
  "summary": {
    "stories": len(grouped),
    "entries": sum(len(cqs) for cqs in grouped.values()),
    "invalid_rows": invalid_rows,
  },
  "by_user_story": grouped,
}

with open(grouped_path, "w", encoding="utf-8") as out:
  json.dump(result, out, ensure_ascii=False, indent=2)
PY

python src/serialize_cq_results_to_rdf.py \
  --input "$GROUPED_OUTPUT_FILE" \
  --output "$RDF_OUTPUT_FILE"

echo "Extraction complete. Results saved to: $OUTPUT_FILE"
echo "Grouped output saved to: $GROUPED_OUTPUT_FILE"
echo "RDF Turtle saved to: $RDF_OUTPUT_FILE"
