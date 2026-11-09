#!/usr/bin/env python3
"""Generate a NeTEx-like PublicationDelivery XML from CSV input.
"""

from __future__ import annotations

import itertools
import numpy as np
import json
import re
import warnings
import pandas as pd
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from shapely import area


NETEX_NS = "http://www.netex.org.uk/netex"
GML_NS = "http://www.opengis.net/gml/3.2"

ns_map = {
    "": NETEX_NS,
    "gml": GML_NS,
}

for prefix, uri in ns_map.items():
    ET.register_namespace(prefix, uri)

def ns_tag(tag: str, ns: str = NETEX_NS) -> str:
    return f"{{{ns}}}{tag}"

@dataclass
class ExportConfig:
    publication_timestamp: str
    participant_ref: str
    description: str
    codespace: str
    version: str
    frame_key: str
    valid_from: str
    valid_to: str
    organisation_name: str
    branding: str
    operator_code: str
    operator_name: str
    operator_url: str
    zone_name: str
    zone_short_name: str
    zone_description: str
    line_code: str
    line_name: str
    maximum_travel_distance: str
    minimum_travel_distance: str
    minimum_pt_travel_time_difference_factor: str
    no_public_transport_window: str
    safe_duration_factor: str
    safe_duration_offset: str
    booking_phone: str
    booking_url: str
    booking_further_details: str
    booking_methods: str
    booking_access: str
    book_when: str
    latest_booking_time: str
    minimum_booking_period: str
    booking_note: str
    vehicle_type_code: str
    vehicle_name: str
    vehicle_description: str
    vehicle_fuel_type: str
    vehicle_transport_mode: str
    passenger_fare_class: str
    passenger_total_capacity: str
    passenger_seating_capacity: str
    passenger_standing_capacity: str
    passenger_special_place_capacity: str
    passenger_push_chair_capacity: str
    passenger_wheelchair_place_capacity: str
    vehicle_has_lift_or_ramp: str
    vehicle_length: str
    vehicle_access_facility_list: str


def slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "unknown"


def add_text(parent: ET.Element, tag: str, text: str, ns: str = NETEX_NS) -> ET.Element:
    elem = ET.SubElement(parent, ns_tag(tag, ns))
    elem.text = text
    return elem


def read_stops(csv_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", sep=';', dtype=str)
        required = {"code", "name", "short_name", "x", "y", "halte", "gebied"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(
                "Stops CSV is missing required columns: " + ", ".join(sorted(missing))
            )
        return df
    except FileNotFoundError:
        print(f"Stops/Adresses CSV file not found: {csv_path}")
        return pd.DataFrame(columns=["code", "name", "short_name", "x", "y", "halte", "gebied"])
    
def read_config(config_path: Path) -> ExportConfig:
    required = {
        "publication_timestamp",
        "participant_ref",
        "description",
        "codespace",
        "version",
        "frame_key",
        "valid_from",
        "valid_to",
        "organisation_name",
        "branding",
        "operator_code",
        "operator_name",
        "operator_url",
        "zone_name",
        "zone_short_name",
        "zone_description",
        "line_code",
        "line_name",
        "safe_duration_factor",
        "safe_duration_offset",
        "booking_phone",
        "booking_url",
        "booking_further_details",
        "booking_methods",
        "booking_access",
        "book_when",
        "latest_booking_time",
        "minimum_booking_period",
        "booking_note",
    }
    optional = {
        "maximum_travel_distance",
        "minimum_travel_distance",
        "minimum_pt_travel_time_difference_factor",
        "no_public_transport_window",
        "gemeentecodes"
    }
    vehicle_defaults = {
        "vehicle_type_code": "flexauto",
        "vehicle_name": "Voertuignaam",
        "vehicle_description": "Voertuigomschrijving",
        "vehicle_fuel_type": "other",
        "vehicle_transport_mode": "bus",
        "passenger_fare_class": "any",
        "passenger_total_capacity": "4",
        "passenger_seating_capacity": "4",
        "passenger_standing_capacity": "0",
        "passenger_special_place_capacity": "2",
        "passenger_push_chair_capacity": "1",
        "passenger_wheelchair_place_capacity": "1",
        "vehicle_has_lift_or_ramp": "True",
        "vehicle_length": "5",
        "vehicle_access_facility_list": "wheelchairLift",
    }

    series_config = pd.read_csv(config_path, encoding="utf-8-sig", sep=';',header=None, index_col=0)[1]
    values = series_config.where(pd.notna(series_config), None).to_dict()
    
    # Quick check for missing columns
    missing_required = required.difference(values.keys())
    if missing_required:
        raise ValueError(
            "Config CSV is missing required columns: " + ", ".join(sorted(missing_required))
            )

    missing_optional = optional.difference(values.keys())
    if missing_optional:
        warnings.warn(
            "Config CSV is missing optional columns: " + ", ".join(sorted(missing_optional)),
            UserWarning,
        )
    # Fill in missing optional values with None
    values.update({key: None for key in missing_optional})
    values.update({key: values.get(key) or default for key, default in vehicle_defaults.items()})

    return ExportConfig(
        publication_timestamp=values["publication_timestamp"],
        participant_ref=values["participant_ref"],
        description=values["description"],
        codespace=values["codespace"],
        version=values["version"],
        frame_key=values["frame_key"],
        valid_from=values["valid_from"],
        valid_to=values["valid_to"],
        organisation_name=values["organisation_name"],
        branding=values["branding"],
        operator_code=values["operator_code"],
        operator_name=values["operator_name"],
        operator_url=values["operator_url"],
        zone_name=values["zone_name"],
        zone_short_name=values["zone_short_name"],
        zone_description=values["zone_description"],
        line_code=values["line_code"],
        line_name=values["line_name"],
        booking_phone=values["booking_phone"],
        booking_url=values["booking_url"],
        booking_further_details=values["booking_further_details"],
        booking_methods=values["booking_methods"],
        booking_access=values["booking_access"],
        book_when=values["book_when"],
        latest_booking_time=values["latest_booking_time"],
        minimum_booking_period=values["minimum_booking_period"],
        booking_note=values["booking_note"],
        vehicle_type_code=values["vehicle_type_code"],
        vehicle_name=values["vehicle_name"],
        vehicle_description=values["vehicle_description"],
        vehicle_fuel_type=values["vehicle_fuel_type"],
        vehicle_transport_mode=values["vehicle_transport_mode"],
        passenger_fare_class=values["passenger_fare_class"],
        passenger_total_capacity=values["passenger_total_capacity"],
        passenger_seating_capacity=values["passenger_seating_capacity"],
        passenger_standing_capacity=values["passenger_standing_capacity"],
        passenger_special_place_capacity=values["passenger_special_place_capacity"],
        passenger_push_chair_capacity=values["passenger_push_chair_capacity"],
        passenger_wheelchair_place_capacity=values["passenger_wheelchair_place_capacity"],
        vehicle_has_lift_or_ramp=values["vehicle_has_lift_or_ramp"],
        vehicle_length=values["vehicle_length"],
        vehicle_access_facility_list=values["vehicle_access_facility_list"],
        safe_duration_factor=values["safe_duration_factor"],
        safe_duration_offset=values["safe_duration_offset"],
        maximum_travel_distance=values["maximum_tavel_distance"],
        minimum_travel_distance=values["minimum_travel_distance"],
        minimum_pt_travel_time_difference_factor=values["minimum_pt_travel_time_difference_factor"],
        no_public_transport_window=values["no_public_transport_window"]
    )

def read_bedieningstijden(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig", sep=';', dtype=str)
    required = {"code", "dagen", "start_time", "end_time", "day_offset"}
    missing = required.difference(df.columns)
    if missing:
            raise ValueError(
                "Bedieningstijden CSV is missing required columns: " + ", ".join(sorted(missing))
            )
    return df

def read_flex_area(csv_path: Path) -> dict:
    try:
        with open(csv_path, 'r') as f:
            area_dict = json.load(f)
        return area_dict
    except FileNotFoundError:
        print(f"Flex area JSON file not found: {csv_path}")
        return {}

def build_xml(stops: pd.DataFrame, hubs: pd.DataFrame, cfg: ExportConfig, bdt: pd.DataFrame,
               flex_area: dict) -> ET.ElementTree:
    root = ET.Element(ns_tag("PublicationDelivery"), {"version": "ntx:1.1"})

    add_text(root, "PublicationTimestamp", cfg.publication_timestamp)
    add_text(root, "ParticipantRef", cfg.participant_ref)
    add_text(root, "Description", cfg.description)

    data_objects = ET.SubElement(root, ns_tag("dataObjects"))
    composite = ET.SubElement(
        data_objects,
        ns_tag("CompositeFrame"),
        {
            "id": f"NL:{cfg.codespace}:CompositeFrame:{cfg.frame_key}",
            "modification": "new",
            "version": cfg.version,
        },
    )

    valid_between = ET.SubElement(composite, ns_tag("ValidBetween"))
    add_text(valid_between, "FromDate", cfg.valid_from)
    add_text(valid_between, "ToDate", cfg.valid_to)

    ET.SubElement(
        composite,
        ns_tag("TypeOfFrameRef"),
        {"version": "9.4.1", "ref": "NL:BISON:TypeOfFrame:NL_TT_BASELINE"},
    )

    frame_defaults = ET.SubElement(composite, ns_tag("FrameDefaults"))
    ET.SubElement(frame_defaults, ns_tag("DefaultCodespaceRef"), {"ref": f"NL:BISON:Codespace:{cfg.codespace}"})
    ET.SubElement(
        frame_defaults,
        ns_tag("DefaultDataSourceRef"),
        {"version": cfg.version, "ref": f"NL:{cfg.codespace}:DataSource:{cfg.codespace}"},
    )
    ET.SubElement(
        frame_defaults,
        ns_tag("DefaultResponsibilitySetRef"),
        {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ResponsibilitySet:{cfg.codespace}"},
    )
    default_locale = ET.SubElement(frame_defaults, ns_tag("DefaultLocale"))
    add_text(default_locale, "TimeZone", "Europe/Amsterdam")
    add_text(default_locale, "DefaultLanguage", "nl")
    add_text(frame_defaults, "DefaultLocationSystem", "EPSG:4326")
    add_text(frame_defaults, "DefaultSystemOfUnits", "SiMetres")
    add_text(frame_defaults, "DefaultCurrency", "EUR")

    frames = ET.SubElement(composite, ns_tag("frames"))

    resource = ET.SubElement(
        frames,
        ns_tag("ResourceFrame"),
        {"id": f"NL:{cfg.codespace}:ResourceFrame:{cfg.frame_key}", "version": cfg.version},
    )
    ET.SubElement(resource, ns_tag("TypeOfFrameRef"), {"version": "9.4.1", "ref": "NL:BISON:TypeOfFrame:NL_TT_RESOURCE"})

    data_sources = ET.SubElement(resource, ns_tag("dataSources"))
    data_source = ET.SubElement(
        data_sources,
        ns_tag("DataSource"),
        {"id": f"NL:{cfg.codespace}:DataSource:{cfg.codespace}", "version": cfg.version},
    )
    add_text(data_source, "Name", cfg.organisation_name)
    add_text(data_source, "ShortName", cfg.codespace)
    add_text(data_source, "Description", cfg.organisation_name)

    responsibility_sets = ET.SubElement(resource, ns_tag("responsibilitySets"))
    resp = ET.SubElement(
        responsibility_sets,
        ns_tag("ResponsibilitySet"),
        {"id": f"NL:{cfg.codespace}:ResponsibilitySet:{cfg.codespace}", "version": cfg.version},
    )
    add_text(resp, "Name", f"Financier {cfg.organisation_name}")
    roles = ET.SubElement(resp, ns_tag("roles"))
    role = ET.SubElement(
        roles,
        ns_tag("ResponsibilityRoleAssignment"),
        {"id": f"NL:{cfg.codespace}:ResponsibilityRoleAssignment:{cfg.codespace}", "version": cfg.version},
    )
    add_text(role, "StakeholderRoleType", "entityLegalOwnership")
    ET.SubElement(
        role,
        ns_tag("TypeOfResponsibilityRoleRef"),
        {"version": "any", "ref": "NL:BISON:TypeOfResponsibilityRole:financing"},
    )
    types_of_value = ET.SubElement(resource, ns_tag("typesOfValue"))
    branding = ET.SubElement(types_of_value, ns_tag("Branding"),
                             {"id": f"NL:{cfg.codespace}:Branding:{cfg.branding}", "version": cfg.version})
    add_text(branding, "Name", cfg.branding)
    organisations = ET.SubElement(resource, ns_tag("organisations"))
    operator = ET.SubElement(
        organisations,
        ns_tag("Operator"),
        {"id": f"NL:{cfg.codespace}:Operator:{cfg.operator_code}", "version": cfg.version},
    )
    add_text(operator, "Name", cfg.operator_name)
    add_text(operator, "ShortName", cfg.operator_code)
    contact = ET.SubElement(operator, ns_tag("CustomerServiceContactDetails"))
    add_text(contact, "Url", cfg.operator_url)

    operational_contexts = ET.SubElement(resource, ns_tag("operationalContexts"))
    context = ET.SubElement(
        operational_contexts,
        ns_tag("OperationalContext"),
        {"id": f"NL:{cfg.codespace}:OperationalContext:BUS", "version": cfg.version},
    )
    add_text(context, "VehicleMode", "bus")

    vehicle_types = ET.SubElement(resource, ns_tag("vehicleTypes"))
    vehicle_type = ET.SubElement(
        vehicle_types,
        ns_tag("VehicleType"),
        {"id": f"NL:{cfg.codespace}:VehicleType:{cfg.vehicle_type_code}", "version": cfg.version},
    )
    add_text(vehicle_type, "BrandingRef", f"NL:{cfg.codespace}:Branding:{cfg.branding}")
    add_text(vehicle_type, "Name", cfg.vehicle_name)
    add_text(vehicle_type, "Description", cfg.vehicle_description)
    add_text(vehicle_type, "FuelType", cfg.vehicle_fuel_type)
    add_text(vehicle_type, "TransportMode", cfg.vehicle_transport_mode)
    
    capacities = ET.SubElement(vehicle_type, ns_tag("capacities"))
    passenger_capacity = ET.SubElement(capacities, ns_tag("PassengerCapacity"))
    add_text(passenger_capacity, "FareClass", cfg.passenger_fare_class)
    add_text(passenger_capacity, "TotalCapacity", cfg.passenger_total_capacity)
    add_text(passenger_capacity, "SeatingCapacity", cfg.passenger_seating_capacity)
    add_text(passenger_capacity, "StandingCapacity", cfg.passenger_standing_capacity)
    add_text(passenger_capacity, "SpecialPlaceCapacity", cfg.passenger_special_place_capacity)
    add_text(passenger_capacity, "PushChairCapacity", cfg.passenger_push_chair_capacity)
    add_text(passenger_capacity, "WheeelchairPlaceCapacity", cfg.passenger_wheelchair_place_capacity)

    add_text(vehicle_type, "HasLiftOrRamp", cfg.vehicle_has_lift_or_ramp)
    add_text(vehicle_type, "Length", cfg.vehicle_length)
    vehicle_facilities = ET.SubElement(vehicle_type, ns_tag("Facilities"))
    service_facility_set = ET.SubElement(vehicle_facilities, ns_tag("ServiceFacilitySet"))
    add_text(service_facility_set, "VehicleAccessFacilityList", cfg.vehicle_access_facility_list)
    
    zones = ET.SubElement(resource, ns_tag("zones"))
    zone = ET.SubElement(
        zones,
        ns_tag("TransportAdministrativeZone"),
        {
            "id": f"NL:{cfg.codespace}:TransportAdministrativeZone:{slugify(cfg.zone_name.lower())}",
            "version": cfg.version,
        },
    )
    add_text(zone, "Name", cfg.zone_name)
    add_text(zone, "ShortName", cfg.zone_short_name)
    add_text(zone, "Description", cfg.zone_description)

    site = ET.SubElement(
        frames,
        ns_tag("SiteFrame"),
        {"id": f"NL:{cfg.codespace}:SiteFrame:{cfg.frame_key}", "version": cfg.version},
    )
    ET.SubElement(site, ns_tag("TypeOfFrameRef"), {"version": "9.4.1", "ref": "BISON:TypeOfFrame:NL_TT_SITE"})

    # maak dictionary van gebieden met hun type
    gebieden = {}
    for gebied in list(stops['gebied'].unique()):
        gebieden[gebied] = {'type': 'haltegebied'}
        gebieden[gebied]['stops'] = stops.loc[stops['gebied'] == gebied]
    for area, area_data in flex_area.items():
        gebieden[area] = {'type': 'oppervlak'}
        gebieden[area]['geometry'] = area_data
    # for hub in hubs.itertuples():
    #     gebieden[hub.code] = {'type': 'hub'}

    #maak lijst van routes    
    hubcodes = [hub.code for hub in hubs.itertuples()]
    interne_gebieden = [gebied for gebied in gebieden.keys() if gebieden[gebied]['type'] != 'hub']
    routes = list(itertools.product(interne_gebieden, repeat=2)) + [(g, h) for g in interne_gebieden for h in hubcodes] + [(h, g) for g in interne_gebieden for h in hubcodes]
    print('Gebieden:', gebieden.keys())
    print('Routes:', routes)
    flexible_stop_places = ET.SubElement(site, ns_tag("flexibleStopPlaces"))

    ## 'Haltegebieden'
    for gebied, gebied_dict in gebieden.items():
        gebied_code = slugify(gebied.lower())
        
        fsp = ET.SubElement(
            flexible_stop_places,
            ns_tag("FlexibleStopPlace"),
            {"id": f"NL:{cfg.codespace}:FlexibleStopPlace:{gebied_code}", "version": cfg.version},
        )
        if gebied_dict['type'] == 'hub':
            add_text(fsp, "Name", f"Hub {gebied}")
        else:
           add_text(fsp, "Name", gebied)
        add_text(fsp, "ShortName", gebied_code)
        add_text(fsp, "TransportMode", "bus")
     
        areas = ET.SubElement(fsp, ns_tag("areas"))
        area = ET.SubElement(areas,ns_tag("FlexibleArea"))
        add_text(area, "ShortName", gebied_code)
        
        if gebied_dict['type'] == 'haltegebied': # or gebied_dict['type'] == 'hub'
            members = ET.SubElement(area, ns_tag("members"))        
            if gebied_dict['type'] == 'haltegebied':
                for stop in gebieden[gebied]['stops'].itertuples():
                    sspr = ET.SubElement(members, ns_tag("ScheduledStopPointRef"), {"ref": f"NL:{cfg.codespace}:ScheduledStopPointRef:{stop.code}", "version": cfg.version})
            if gebied_dict['type'] == 'hub':
                sspr = ET.SubElement(members, ns_tag("ScheduledStopPointRef"), {"ref": f"NL:{cfg.codespace}:ScheduledStopPointRef:{gebied}", "version": cfg.version})
            
        if gebied_dict['type'] == 'oppervlak':
            print('Processing gebied:', gebied)
            print('Gebied type:', gebied_dict['type'])

            polygon = ET.SubElement(area, ns_tag("Polygon", ns = ns_map["gml"]), {ns_tag("id", ns = ns_map["gml"]): f"NL_{cfg.codespace}_FlexibleArea_{slugify(gebied)}"})
            exterior = ET.SubElement(polygon, ns_tag("exterior", ns = ns_map["gml"]))
            linear_ring = ET.SubElement(exterior, ns_tag("LinearRing", ns = ns_map["gml"]))
            pos_list = ET.SubElement(linear_ring, ns_tag("posList", ns = ns_map["gml"]))
            pos_list.text = gebied_dict['geometry']
        
        add_text(area, "BoardingUse", "true")
        add_text(area, "AlightingUse", "true")
    
    service = ET.SubElement(
        frames,
        ns_tag("ServiceFrame"),
        {"id": f"NL:{cfg.codespace}:ServiceFrame:{cfg.frame_key}", "version": cfg.version},
    )


    lines = ET.SubElement(service, ns_tag("lines"))
    line = ET.SubElement(
        lines,
        ns_tag("Line"),
        {"id": f"NL:{cfg.codespace}:Line:{cfg.line_code}", "version": cfg.version},
    )
    line_ext = ET.SubElement(line, ns_tag("Extensions"))
    if int(cfg.maximum_travel_distance) > 0 :
        print(cfg.maximum_travel_distance)
    add_text(line_ext, "MaximumTravelDistance", cfg.maximum_travel_distance)
    if int(cfg.minimum_travel_distance) > 0:
        print(cfg.minimum_travel_distance)
        add_text(line_ext, "MinimumTravelDistance", cfg.minimum_travel_distance)
    if float(cfg.minimum_pt_travel_time_difference_factor) > 0:
        add_text(line_ext, "MinimumPtTravelTimeDifferenceFactor", cfg.minimum_pt_travel_time_difference_factor)
    if int(cfg.no_public_transport_window) > 0:
        add_text(line_ext, "NoPublicTransportWindow", cfg.no_public_transport_window)
    add_text(line,"BrandingRef",f"NL:{cfg.codespace}:Branding:{cfg.branding}")
    add_text(line, "Name", cfg.line_name)
    add_text(line, "TransportMode", "bus")
    ET.SubElement(
        line,
        ns_tag("OperatorRef"),
        {"version": cfg.version, "ref": f"NL:{cfg.codespace}:Operator:{cfg.operator_code}"},
    )

    ET.SubElement(line, ns_tag("TypeOfServiceRef"), {"version": "any", "ref": "NL:BISON:TypeOfService:Flex"})
    add_text(line, "Monitored", "false")

    accessibility = ET.SubElement(
        line,
        ns_tag("AccessibilityAssessment"),
        {"id": f"NL:{cfg.codespace}:AccessibilityAssessment:{cfg.frame_key}", "version": cfg.version},
    )
    add_text(accessibility, "MobilityImpairedAccess", "true")

    booking_arrangements = ET.SubElement(line, ns_tag("bookingArrangements"))
    booking = ET.SubElement(
        booking_arrangements,
        ns_tag("BookingArrangement"),
        {"id": f"NL:{cfg.codespace}:BookingArrangement:{cfg.frame_key}", "version": cfg.version},
    )
    booking_contact = ET.SubElement(booking, ns_tag("BookingContact"))
    add_text(booking_contact, "Phone", cfg.booking_phone)
    add_text(booking_contact, "Url", cfg.booking_url)
    add_text(booking_contact, "FurtherDetails", cfg.booking_further_details)
    add_text(booking, "BookingMethods", cfg.booking_methods)
    add_text(booking, "BookingAccess", cfg.booking_access)
    add_text(booking, "BookWhen", cfg.book_when)
    add_text(booking, "LatestBookingTime", cfg.latest_booking_time)
    add_text(booking, "MinimumBookingPeriod", cfg.minimum_booking_period)
    add_text(booking, "BookingUrl", cfg.booking_url)
    add_text(booking, "BookingNote", cfg.booking_note)

    haltes = stops.loc[stops['halte'] == 'True'].copy()
    haltes = pd.concat([haltes, hubs])

    scheduled_stop_points = ET.SubElement(service, ns_tag("scheduledStopPoints"))
    #Maak ScheduledStopPoints voor oppervlakte gebieden
    for gebied, gebied_data in gebieden.items():
        if gebied_data['type'] != 'oppervlak':
            continue
        gebied_code = slugify(gebied.lower())
        ssp = ET.SubElement(
            scheduled_stop_points,
            ns_tag("ScheduledStopPoint"),
            {"id": f"NL:{cfg.codespace}:ScheduledStopPoint:{gebied_code}", "version": cfg.version},
        )
        add_text(ssp, "Name", gebied)
        add_text(ssp, "ForAlighting", "true")
        add_text(ssp, "ForBoarding", "true")

    # Maak ScheduledStopPoints voor haltes (stops uit haltegebieden en hubs)
    for halte in haltes.itertuples():
        ssp = ET.SubElement(
            scheduled_stop_points,
            ns_tag("ScheduledStopPoint"),
            {"id": f"NL:{cfg.codespace}:ScheduledStopPoint:{halte.code}", "version": cfg.version},
        )
        pcs = ET.SubElement(ssp, ns_tag("privateCodes"))
        pc = ET.SubElement(pcs, ns_tag("PrivateCode"), {"type": "UserStopcode"})
        pc.text = f"{halte.code}"

        add_text(ssp, "Name", halte.name)

        location = ET.SubElement(ssp, ns_tag("Location"))
        add_text(location, "pos", f"{halte.y} {halte.x}", ns=ns_map["gml"])

        add_text(ssp, "ForAlighting", "true")
        add_text(ssp, "ForBoarding", "true")

    
    stop_assignments = ET.SubElement(service, ns_tag("stopAssignments"))
    for gebied, gebied_data in gebieden.items():
        gebied_code = slugify(gebied.lower())
        FSA = ET.SubElement(stop_assignments, ns_tag("FlexibleStopAssignment"), {"id": f"NL:{cfg.codespace}:FlexibleStopAssignment:{gebied_code}", "version": cfg.version})
        ET.SubElement(FSA, ns_tag("ScheduledStopPointRef"), {"version": cfg.version
        , "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{gebied_code}"})
        ET.SubElement(FSA, ns_tag("FlexibleStopPlaceRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:FlexibleStopPlace:{gebied_code}"})

    for row in haltes.itertuples():        
        PSA = ET.SubElement(stop_assignments, ns_tag("PassengerStopAssignment"), {"id": f"NL:{cfg.codespace}:PassengerStopAssignment:{row.code}", "version": cfg.version})
        ET.SubElement(PSA, ns_tag("ScheduledStopPointRef"), {"version": cfg.version
        , "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{row.code}"})
        ET.SubElement(PSA, ns_tag("StopPlaceRef"), {"version": cfg.version, "ref": f"NL:CHB:StopPlace:{row.code}"})
    
    
    timingLinks = ET.SubElement(service,ns_tag("timingLinks"))

    journeyPatterns = ET.SubElement(service,ns_tag("journeyPatterns"))
    
    for route in routes:
        print(f'Route van {route[0]} naar {route[1]} toevoegen.')
        tl = ET.SubElement(timingLinks, ns_tag("TimingLink"), {"id": f"NL:{cfg.codespace}:TimingLink:{route[0]}_{route[1]}", "version": cfg.version})
        ET.SubElement(tl, ns_tag("FromPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[0]}"})
        ET.SubElement(tl, ns_tag("ToPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[1]}"})

        SJP = ET.SubElement(journeyPatterns, ns_tag("ServiceJourneyPattern"), {"id": f"NL:{cfg.codespace}:ServiceJourneyPattern:{route[0]}_{route[1]}", "version": cfg.version})
        pointsInSequence = ET.SubElement(SJP, ns_tag("pointsInSequence"))
        SPJIP_A = ET.SubElement(pointsInSequence, ns_tag("StopPointInJourneyPattern"), {"id": f"NL:{cfg.codespace}:StopPointInJourneyPattern:{route[0]}_{route[1]}_1", "version": cfg.version})
        ET.SubElement(SPJIP_A, ns_tag("ScheduledStopPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[0]}"})
        ET.SubElement(SPJIP_A, ns_tag("OnwardTimingLinkRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:TimingLink:{route[0]}_{route[1]}"})
        add_text(SPJIP_A, "ForAlighting", "false")
        add_text(SPJIP_A, "ForBoarding", "true")

        def add_flexible_point_properties(route_point, gebieden, SJIP):
            try:
                gebiedstype = gebieden[route_point]['type']
            except KeyError:
                gebiedstype = None
            if gebiedstype == 'oppervlak':
                #print(f"Adding flexible point properties for oppervlakte at route point {route_point}")
                FPP = ET.SubElement(SJIP, ns_tag("FlexiblePointProperties"))
                add_text(FPP, "PointsStandingForAZone", 'true')
                add_text(FPP, "ZoneContainingStops", 'false')
            if gebiedstype == 'haltegebied':
                #print(f"Adding flexible point properties for haltegebied at route point {route_point}")
                FPP = ET.SubElement(SJIP, ns_tag("FlexiblePointProperties"))
                add_text(FPP, "PointsStandingForAZone", 'true')
                add_text(FPP, "ZoneContainingStops", 'true')
            elif gebiedstype == 'hub':
                pass

        add_flexible_point_properties(route[0], gebieden, SPJIP_A)

        SPJIP_B = ET.SubElement(pointsInSequence, ns_tag("StopPointInJourneyPattern"), {"id": f"NL:{cfg.codespace}:StopPointInJourneyPattern:{route[0]}_{route[1]}_2", "version": cfg.version})
        ET.SubElement(SPJIP_B, ns_tag("ScheduledStopPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[1]}"})
        add_text(SPJIP_B, "ForAlighting", "true")
        add_text(SPJIP_B, "ForBoarding", "false")

        add_flexible_point_properties(route[1], gebieden, SPJIP_B)
    
    timetable = ET.SubElement(frames, ns_tag("TimetableFrame"), {"id": f"NL:{cfg.codespace}:TimetableFrame:{cfg.frame_key}", "version": cfg.version})
    ET.SubElement(timetable, ns_tag("TypeOfFrameRef"), {"version": "9.4.1", "ref": "NL:BISON:TypeOfFrame:NL_TT_TIMETABLE"})
    add_text(timetable, "Monitored", f"false")
    CVC = ET.SubElement(timetable, ns_tag("contentValidityConditions"))

    for _, row in bdt.iterrows():            
        AC = ET.SubElement(CVC, ns_tag("AvailabilityCondition"), {"id": f"NL:{cfg.codespace}:AvailabilityCondition:{row['code']}", "version": cfg.version})
        add_text(AC, "FromDate", cfg.valid_from)
        add_text(AC, "ToDate", cfg.valid_to)
        add_text(AC, "ValidDayBits", row['dagen'] * 52)  # Every day of the year
        timebands = ET.SubElement(AC, ns_tag("timebands"))
        timeband = ET.SubElement(timebands, ns_tag("Timeband"), {"id": f"NL:{cfg.codespace}:Timeband:{row['code']}", "version": cfg.version})
        add_text(timeband, "StartTime", row["start_time"])
        add_text(timeband, "EndTime", row["end_time"])
        if row["day_offset"] != 0:
            add_text(timeband, "DayOffset", str(row["day_offset"]))

    vehicle_journeys = ET.SubElement(timetable, ns_tag("vehicleJourneys"))
    
    for route in routes:
        SJ = ET.SubElement(vehicle_journeys, ns_tag("ServiceJourney"), {"id": f"NL:{cfg.codespace}:ServiceJourney:{route[0]}_{route[1]}", "version": cfg.version})
        validityConditions = ET.SubElement(SJ, ns_tag("validityConditions"))
        for _, row in bdt.iterrows():      
            ET.SubElement(validityConditions, ns_tag("AvailabilityConditionRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:AvailabilityCondition:{row['code']}"})
        ET.SubElement(SJ, ns_tag("ServiceJourneyPatternRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ServiceJourneyPattern:{route[0]}_{route[1]}"})
        ET.SubElement(SJ, ns_tag("VehicleTypeRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:VehicleType:{cfg.vehicle_type_code}"})
        ET.SubElement(SJ, ns_tag("LineRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:FlexibleLine:{cfg.line_code}"})
          
        ET.SubElement(SJ, ns_tag("FlexibleServicePropertiesRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:FlexibleServiceProperties:{cfg.frame_key}"})
    
    flexibleServiceProperties = ET.SubElement(timetable, ns_tag("flexibleServiceProperties"),{"id": f"NL:{cfg.codespace}:FlexibleServiceProperties:{cfg.frame_key}", "version": cfg.version})
    add_text(flexibleServiceProperties, "FlexibleServiceType", "dynamicPassingTimes")
    FSP_Ext = ET.SubElement(flexibleServiceProperties, ns_tag("Extensions"))
    add_text(FSP_Ext, "SafeDurationFactor", f"{cfg.safe_duration_factor}")
    add_text(FSP_Ext, "SafeDurationOffset", f"{cfg.safe_duration_offset}")  
    return ET.ElementTree(root)


def mains_tag() -> None:
    pass

if __name__ == "__main__":
    project = 'FlexRRReis_RH'
    config_path = Path(f'config_{project}.csv')
    flex_area_path = Path(f'flex_area_{project}.json')
    
    stops = read_stops(Path(f'stops_{project}.csv'))
    hubs = read_stops(Path(f'hubs_{project}.csv'))
    adresses = read_stops(Path(f'adresses_{project}.csv'))
    cfg = read_config(config_path)
    bdt = read_bedieningstijden(Path(f'bedieningstijden_{project}.csv'))
    flex_area = read_flex_area(flex_area_path)
    
    print('Read input data: {} stops, config with frame key {}, and {} bedieningstijden'.format(len(stops), cfg.frame_key, len(bdt)))
    tree = build_xml(stops, hubs, cfg, bdt, flex_area)
    ET.indent(tree, space="    ")

    output_name= Path(f'NeTEx_PFL_{project}_{cfg.publication_timestamp.replace('-','')[0:8]}.xml')
    tree.write(output_name, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {len(stops)} stops records to {output_name}")