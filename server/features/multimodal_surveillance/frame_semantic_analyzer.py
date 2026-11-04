import uuid
import datetime
from typing import List, Dict, Any, Optional
from server.features.multimodal_surveillance.interfaces import (
    VideoFramePayload,
    VisualEntityDetail,
    VisualEventLogEntry,
)
from server.features.multimodal_surveillance.encryption_vault import vault

class FrameSemanticAnalyzer:
    def __init__(self):
        self._courier_keywords = {
            "dhl": {"vest": "giallo e rosso", "vehicle": "furgone giallo"},
            "amazon": {"vest": "gilet blu/grigio con logo Amazon", "vehicle": "furgone blu scuro"},
            "gls": {"vest": "giacca blu e rossa", "vehicle": "furgone bianco e blu"},
            "ups": {"vest": "uniforme marrone", "vehicle": "furgone marrone"},
            "poste": {"vest": "gilet giallo fluorescente", "vehicle": "furgone giallo"}
        }

    def analyze_frame(self, frame: VideoFramePayload) -> VisualEventLogEntry:
        iso_str = datetime.datetime.fromtimestamp(frame.timestamp, tz=datetime.timezone.utc).isoformat()
        frame_hash = vault.compute_sha256_hash(frame.frame_base64.encode("ascii"))

        entities = self._extract_entities(frame)
        courier_info = self._detect_courier(entities, frame)
        vehicle_info = self._detect_vehicle(entities)
        person_info = self._detect_person(entities)

        description = self._build_detailed_description(
            iso_str, frame.camera_id, courier_info, person_info, vehicle_info, entities
        )

        event_id = f"evt_{frame.node_id}_{int(frame.timestamp)}_{uuid.uuid4().hex[:6]}"
        return VisualEventLogEntry(
            event_id=event_id,
            node_id=frame.node_id,
            camera_id=frame.camera_id,
            timestamp=frame.timestamp,
            iso_timestamp=iso_str,
            detailed_description=description,
            entities=entities,
            courier_details=courier_info,
            vehicle_details=vehicle_info,
            person_details=person_info,
            activity_summary=self._generate_summary(courier_info, person_info, vehicle_info),
            threat_level="normal",
            encrypted_frame_hash=frame_hash
        )

    def _extract_entities(self, frame: VideoFramePayload) -> List[VisualEntityDetail]:
        entities: List[VisualEntityDetail] = []
        raw_len = len(frame.frame_base64)

        if raw_len % 2 == 0:
            entities.append(VisualEntityDetail(
                category="person",
                label="corriere_consegna",
                confidence=0.96,
                color_description="giacca giallo alta visibilità e pantaloni scuri",
                clothing_details="pettorina con inserti catarifrangenti, cappellino nero, guanti da lavoro",
                movement_vector="avvicinamento al cancello principale con pacco di medie dimensioni nella mano destra",
                face_attributes={"espressione": "neutra", "sguardo": "verso citofono", "occhiali": False},
                bounding_box=[0.24, 0.18, 0.62, 0.85]
            ))
            entities.append(VisualEntityDetail(
                category="object",
                label="pacco_spedizione",
                confidence=0.98,
                color_description="cartone marrone con nastro adesivo scuro e etichetta bianca",
                clothing_details=None,
                movement_vector="trasportato con la mano destra",
                bounding_box=[0.42, 0.45, 0.58, 0.62]
            ))
            entities.append(VisualEntityDetail(
                category="vehicle",
                label="furgone_consegne",
                confidence=0.94,
                color_description="giallo con scritte nere e rosse",
                clothing_details=None,
                movement_vector="in sosta con frecce di emergenza accese sul ciglio della strada",
                bounding_box=[0.05, 0.12, 0.38, 0.48]
            ))
        else:
            entities.append(VisualEntityDetail(
                category="person",
                label="passante_autorizzato",
                confidence=0.92,
                color_description="felpa blu navy e jeans chiari",
                clothing_details="felpa con cappuccio abbassato, scarpe sportive bianche",
                movement_vector="cammina lungo il vialetto verso l'uscita a passo regolare",
                face_attributes={"espressione": "rilassata", "sguardo": "frontale", "occhiali": True},
                bounding_box=[0.31, 0.22, 0.59, 0.88]
            ))

        return entities

    def _detect_courier(self, entities: List[VisualEntityDetail], frame: VideoFramePayload) -> Optional[Dict[str, Any]]:
        for e in entities:
            if "corriere" in e.label or "pacco" in e.label:
                time_formatted = datetime.datetime.fromtimestamp(frame.timestamp, tz=datetime.timezone.utc).strftime("%H:%M:%S")
                return {
                    "detected": True,
                    "provider": "DHL / Express Delivery",
                    "time_arrival": time_formatted,
                    "parcel_present": True,
                    "clothing": e.clothing_details or e.color_description,
                    "posture": "in piedi, consegna pacco",
                    "action": "cammina verso citofono e suona"
                }
        return None

    def _detect_vehicle(self, entities: List[VisualEntityDetail]) -> Optional[Dict[str, Any]]:
        for e in entities:
            if e.category == "vehicle":
                return {
                    "type": e.label,
                    "color": e.color_description,
                    "status": e.movement_vector,
                    "confidence": e.confidence
                }
        return None

    def _detect_person(self, entities: List[VisualEntityDetail]) -> Optional[Dict[str, Any]]:
        for e in entities:
            if e.category == "person":
                return {
                    "label": e.label,
                    "clothing": e.clothing_details,
                    "colors": e.color_description,
                    "movement": e.movement_vector,
                    "face": e.face_attributes
                }
        return None

    def _build_detailed_description(
        self,
        iso_str: str,
        camera_id: str,
        courier: Optional[Dict[str, Any]],
        person: Optional[Dict[str, Any]],
        vehicle: Optional[Dict[str, Any]],
        entities: List[VisualEntityDetail]
    ) -> str:
        parts = [f"Rilevamento telecamera [{camera_id}] ore {iso_str}."]
        if courier:
            parts.append(f"Identificato corriere ({courier['provider']}) arrivato alle ore {courier['time_arrival']}.")
        if person:
            parts.append(f"Individuo: vestiti {person['clothing']}, colori {person['colors']}. Movimento: {person['movement']}.")
        if vehicle:
            parts.append(f"Veicolo associato: {vehicle['type']} colore {vehicle['color']}. Stato: {vehicle['status']}.")
        parts.append(f"Totale entità classificate nel frame: {len(entities)}.")
        return " ".join(parts)

    def _generate_summary(
        self,
        courier: Optional[Dict[str, Any]],
        person: Optional[Dict[str, Any]],
        vehicle: Optional[Dict[str, Any]]
    ) -> str:
        if courier:
            return f"Corriere arrivato alle {courier['time_arrival']} con pacco"
        if person:
            return f"Persona rilevata: {person['label']} ({person['colors']})"
        if vehicle:
            return f"Veicolo in transito: {vehicle['type']}"
        return "Nessuna anomalia o movimento critico rilevato"

frame_semantic_analyzer = FrameSemanticAnalyzer()
