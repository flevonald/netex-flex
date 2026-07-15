#!/usr/bin/env python3
"""Generate a NeTEx-like PublicationDelivery XML from CSV input.
"""

from __future__ import annotations

import itertools
import json
import re
import pandas as pd
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


NETEX_NS = "http://www.netex.org.uk/netex"
GML_NS = "http://www.opengis.net/gml/3.2"

ET.register_namespace("", NETEX_NS)
ET.register_namespace("gml", GML_NS)


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
    operator_code: str
    operator_name: str
    operator_url: str
    zone_name: str
    zone_short_name: str
    zone_description: str
    line_code: str
    line_name: str
    maximumtraveldistance: str
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


def n(tag: str) -> str:
    return f"{{{NETEX_NS}}}{tag}"


def g(tag: str) -> str:
    return f"{{{GML_NS}}}{tag}"


def slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "unknown"


def add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    elem = ET.SubElement(parent, n(tag))
    elem.text = text
    return elem


def read_stops(csv_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", sep=',', dtype=str)
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
        "operator_code",
        "operator_name",
        "operator_url",
        "zone_name",
        "zone_short_name",
        "zone_description",
        "line_code",
        "line_name",
        "maximumtraveldistance",
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

    series_config = pd.read_csv(config_path, encoding="utf-8-sig", sep=';',header=None, index_col=0)[1]
    values = series_config.to_dict() 

    # Quick check for missing columns
    missing = required.difference(values.keys())
    if missing:
        raise ValueError(
            "Config CSV is missing required columns: " + ", ".join(sorted(missing))
            )
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
        maximumtraveldistance=values["maximumtraveldistance"],
        safe_duration_factor=values["safe_duration_factor"],
        safe_duration_offset=values["safe_duration_offset"],
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

def build_xml(stops: pd.DataFrame, cfg: ExportConfig, bdt: pd.DataFrame) -> ET.ElementTree:
    root = ET.Element(n("PublicationDelivery"), {"version": "ntx:1.1"})

    add_text(root, "PublicationTimestamp", cfg.publication_timestamp)
    add_text(root, "ParticipantRef", cfg.participant_ref)
    add_text(root, "Description", cfg.description)

    data_objects = ET.SubElement(root, n("dataObjects"))
    composite = ET.SubElement(
        data_objects,
        n("CompositeFrame"),
        {
            "id": f"NL:{cfg.codespace}:CompositeFrame:{cfg.frame_key}",
            "modification": "new",
            "version": cfg.version,
        },
    )

    valid_between = ET.SubElement(composite, n("ValidBetween"))
    add_text(valid_between, "FromDate", cfg.valid_from)
    add_text(valid_between, "ToDate", cfg.valid_to)

    ET.SubElement(
        composite,
        n("TypeOfFrameRef"),
        {"version": "9.4.0", "ref": "NL:BISON:TypeOfFrame:NL_TT_BASELINE"},
    )

    frame_defaults = ET.SubElement(composite, n("FrameDefaults"))
    ET.SubElement(frame_defaults, n("DefaultCodespaceRef"), {"ref": f"NL:BISON:Codespace:{cfg.codespace}"})
    ET.SubElement(
        frame_defaults,
        n("DefaultDataSourceRef"),
        {"version": cfg.version, "ref": f"NL:{cfg.codespace}:DataSource:{cfg.codespace}"},
    )
    ET.SubElement(
        frame_defaults,
        n("DefaultResponsibilitySetRef"),
        {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ResponsibilitySet:{cfg.codespace}"},
    )
    default_locale = ET.SubElement(frame_defaults, n("DefaultLocale"))
    add_text(default_locale, "TimeZone", "Europe/Amsterdam")
    add_text(default_locale, "DefaultLanguage", "nl")
    add_text(frame_defaults, "DefaultLocationSystem", "EPSG:4326")
    add_text(frame_defaults, "DefaultSystemOfUnits", "SiMetres")
    add_text(frame_defaults, "DefaultCurrency", "EUR")

    frames = ET.SubElement(composite, n("frames"))

    resource = ET.SubElement(
        frames,
        n("ResourceFrame"),
        {"id": f"NL:{cfg.codespace}:ResourceFrame:{cfg.frame_key}", "version": cfg.version},
    )
    ET.SubElement(resource, n("TypeOfFrameRef"), {"version": "9.4.0", "ref": "NL:BISON:TypeOfFrame:NL_TT_RESOURCE"})

    data_sources = ET.SubElement(resource, n("dataSources"))
    data_source = ET.SubElement(
        data_sources,
        n("DataSource"),
        {"id": f"NL:{cfg.codespace}:DataSource:{cfg.codespace}", "version": cfg.version},
    )
    add_text(data_source, "Name", cfg.organisation_name)
    add_text(data_source, "ShortName", cfg.codespace)
    add_text(data_source, "Description", cfg.organisation_name)

    responsibility_sets = ET.SubElement(resource, n("responsibilitySets"))
    resp = ET.SubElement(
        responsibility_sets,
        n("ResponsibilitySet"),
        {"id": f"NL:{cfg.codespace}:ResponsibilitySet:{cfg.codespace}", "version": cfg.version},
    )
    add_text(resp, "Name", f"Financier {cfg.organisation_name}")
    roles = ET.SubElement(resp, n("roles"))
    role = ET.SubElement(
        roles,
        n("ResponsibilityRoleAssignment"),
        {"id": f"NL:{cfg.codespace}:ResponsibilityRoleAssignment:{cfg.codespace}", "version": cfg.version},
    )
    add_text(role, "StakeholderRoleType", "entityLegalOwnership")
    ET.SubElement(
        role,
        n("TypeOfResponsibilityRoleRef"),
        {"version": "any", "ref": "NL:BISON:TypeOfResponsibilityRole:financing"},
    )

    organisations = ET.SubElement(resource, n("organisations"))
    operator = ET.SubElement(
        organisations,
        n("Operator"),
        {"id": f"NL:{cfg.codespace}:Operator:{cfg.operator_code}", "version": cfg.version},
    )
    add_text(operator, "Name", cfg.operator_name)
    add_text(operator, "ShortName", cfg.operator_code)
    contact = ET.SubElement(operator, n("CustomerServiceContactDetails"))
    add_text(contact, "Url", cfg.operator_url)

    operational_contexts = ET.SubElement(resource, n("operationalContexts"))
    context = ET.SubElement(
        operational_contexts,
        n("OperationalContext"),
        {"id": f"NL:{cfg.codespace}:OperationalContext:BUS", "version": cfg.version},
    )
    add_text(context, "VehicleMode", "bus")

    zones = ET.SubElement(resource, n("zones"))
    zone = ET.SubElement(
        zones,
        n("TransportAdministrativeZone"),
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
        n("SiteFrame"),
        {"id": f"NL:{cfg.codespace}:SiteFrame:{cfg.frame_key}", "version": cfg.version},
    )
    ET.SubElement(site, n("TypeOfFrameRef"), {"version": "9.4.0", "ref": "NL:BISON:TypeOfFrame:NL_TT_SITE"})
    flexible_stop_places = ET.SubElement(site, n("flexibleStopPlaces"))
    service = ET.SubElement(
        frames,
        n("ServiceFrame"),
        {"id": f"NL:{cfg.codespace}:ServiceFrame:{cfg.frame_key}", "version": cfg.version},
    )
    stop_assignments = ET.SubElement(service, n("stopAssignments"))

    gebieden = list(stops['gebied'].unique())
    if 'hubs' in gebieden:
        gebieden.remove('hubs')
    
    for gebied in gebieden:
        gebied_code = slugify(gebied)
        FSA = ET.SubElement(stop_assignments, n("FlexibleStopAssignment"), {"id": f"NL:{cfg.codespace}:FlexibleStopAssignment:{gebied_code}", "version": cfg.version})
        ET.SubElement(FSA, n("ScheduledStopPointRef"), {"version": cfg.version
        , "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{gebied_code}"})
        ET.SubElement(FSA, n("FlexibleStopPlaceRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:FlexibleStopPlace:{gebied_code}"})

        fsp = ET.SubElement(
            flexible_stop_places,
            n("FlexibleStopPlace"),
            {"id": f"NL:{cfg.codespace}:FlexibleStopPlace:{gebied_code}", "version": cfg.version},
        )
        add_text(fsp, "Name", gebied)
        add_text(fsp, "ShortName", gebied_code)
        add_text(fsp, "TransportMode", "bus")

        areas = ET.SubElement(fsp, n("areas"))
        area = ET.SubElement(areas,n("FlexibleArea")            
        )
        add_text(area, "Name", gebied)
        add_text(area, "ShortName", gebied_code)

        members = ET.SubElement(area, n("members"))
        for adress in stops[stops['gebied'] == gebied].itertuples():
            sspr = ET.SubElement(members, n("member"), {"id": f"NL:{cfg.codespace}:ScheduledStopPointRef:{adress.code}", "version": cfg.version})

        add_text(area, "BoardingUse", "true")
        add_text(area, "AlightingUse", "true")

    haltes = stops.loc[stops['halte'] == True].copy()
    for row in haltes.itertuples(name='halte'):
        
        PSA = ET.SubElement(stop_assignments, n("PassengerStopAssignment"), {"id": f"NL:{cfg.codespace}:PassengerStopAssignment:{row.code}", "version": cfg.version})
        ET.SubElement(PSA, n("ScheduledStopPointRef"), {"version": cfg.version
        , "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{row.code}"})
        ET.SubElement(PSA, n("StopPlaceRef"), {"version": cfg.version, "ref": f"NL:CHB:StopPlace:{row.code}"})
 
    hubs = stops.loc[stops['gebied'] == 'hubs'].copy()
    for row in haltes.itertuples(name='hub'):
        
        fsp = ET.SubElement(
            flexible_stop_places,
            n("FlexibleStopPlace"),
            {"id": f"NL:{cfg.codespace}:FlexibleStopPlace:{row.code}", "version": cfg.version},
        )
        add_text(fsp, "Name", row.name)
        add_text(fsp, "ShortName", slugify(row.name))
        add_text(fsp, "TransportMode", "bus")

        areas = ET.SubElement(fsp, n("areas"))
        area = ET.SubElement(areas,n("FlexibleArea"))
        add_text(area, "Name", row.name)
        add_text(area, "ShortName", slugify(row.name))
        members = ET.SubElement(area, n("members"))
        sspr = ET.SubElement(members, n("member"), {"id": f"NL:{cfg.codespace}:ScheduledStopPointRef:{row.code}", "version": cfg.version})
        add_text(area, "BoardingUse", "true")
        add_text(area, "AlightingUse", "true")

    ET.SubElement(service, n("TypeOfFrameRef"), {"version": "9.4.0", "ref": "NL:BISON:TypeOfFrame:NL_TT_SERVICE"})
    lines = ET.SubElement(service, n("lines"))
    line = ET.SubElement(
        lines,
        n("Line"),
        {"id": f"NL:{cfg.codespace}:Line:{cfg.line_code}", "version": cfg.version},
    )
    line_ext = ET.SubElement(line, n("Extensions"))
    add_text(line_ext, "MaximumTravelDistance", cfg.maximumtraveldistance)

    add_text(line, "Name", cfg.line_name)
    add_text(line, "TransportMode", "bus")
    ET.SubElement(
        line,
        n("OperatorRef"),
        {"version": "any", "ref": f"NL:{cfg.codespace}:Operator:{cfg.operator_code}"},
    )
    ET.SubElement(line, n("TypeOfServiceRef"), {"version": "any", "ref": "NL:BISON:TypeOfService:Flex"})
    add_text(line, "Monitored", "false")

    accessibility = ET.SubElement(
        line,
        n("AccessibilityAssessment"),
        {"id": f"NL:{cfg.codespace}:AccessibilityAssessment:{cfg.frame_key}", "version": cfg.version},
    )
    add_text(accessibility, "MobilityImpairedAccess", "true")

    booking_arrangements = ET.SubElement(line, n("bookingArrangements"))
    booking = ET.SubElement(
        booking_arrangements,
        n("BookingArrangement"),
        {"id": f"NL:{cfg.codespace}:BookingArrangement:{cfg.frame_key}", "version": cfg.version},
    )
    booking_contact = ET.SubElement(booking, n("BookingContact"))
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

    scheduled_stop_points = ET.SubElement(service, n("scheduledStopPoints"))
    for stop in stops.itertuples():
        ssp = ET.SubElement(
            scheduled_stop_points,
            n("ScheduledStopPoint"),
            {"id": f"NL:{cfg.codespace}:ScheduledStopPoint:{stop.code}", "version": cfg.version},
        )
        pcs = ET.SubElement(ssp, n("privateCodes"))
        if stop.gebied == 'hubs':
            pc = ET.SubElement(pcs, n("PrivateCode"), {"type": "StopPlaceCode"})
            pc.text = f"code:{stop.code}"
        pc = ET.SubElement(pcs, n("PrivateCode"), {"type": "UserStopCode"})
        pc.text = f"code:{stop.code}"

        add_text(ssp, "Name", stop.name)

        location = ET.SubElement(ssp, n("Location"))
        add_text(location, "gml:pos", f"{stop.x} {stop.y}")

        add_text(ssp, "ForAlighting", "true")
        add_text(ssp, "ForBoarding", "true")
    
    timingLinks = ET.SubElement(service,n("timingLinks"))

    journeyPatterns = ET.SubElement(service,n("journeyPatterns"))

    timetable = ET.SubElement(service, n("timetableFrame"), {"id": f"NL:{cfg.codespace}:TimetableFrame:{cfg.frame_key}", "version": cfg.version})
    ET.SubElement(timetable, n("TypeOfFrameRef"), {"version": "9.4.0", "ref": "NL:BISON:TypeOfFrame:NL_TT_TIMETABLE"})
    add_text(timetable, "Monitored", f"false")
    vehicle_journeys = ET.SubElement(timetable, n("vehicleJourneys"))

    gebiedscodes = [gebied for gebied in gebieden]
    hubcodes = [hub.code for hub in hubs.itertuples()]
    routes = list(itertools.product(gebiedscodes, repeat=2)) + [(g, h) for g in gebiedscodes for h in hubcodes] + [(h, g) for g in gebiedscodes for h in hubcodes]
    for route in routes:
        print(f'Route van {route[0]} naar {route[1]} toevoegen.')
        tl = ET.SubElement(timingLinks, n("TimingLink"), {"id": f"NL:{cfg.codespace}:TimingLink:{route[0]}_{route[1]}", "version": cfg.version})
        ET.SubElement(tl, n("FromPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[0]}"})
        ET.SubElement(tl, n("ToPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[1]}"})

        SJP = ET.SubElement(journeyPatterns, n("ServiceJourneyPattern"), {"id": f"NL:{cfg.codespace}:ServiceJourneyPattern:{route[0]}_{route[1]}", "version": cfg.version})
        pointsInSequence = ET.SubElement(SJP, n("pointsInSequence"))
        SPJIP_A = ET.SubElement(pointsInSequence, n("StopPointInJourneyPattern"), {"id": f"NL:{cfg.codespace}:StopPointInJourneyPattern:{route[0]}_{route[1]}_1", "version": cfg.version})
        ET.SubElement(SPJIP_A, n("ScheduledStopPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[0]}"})
        ET.SubElement(SPJIP_A, n("OnwardTimingLinkRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:TimingLink:{route[0]}_{route[1]}"})
        add_text(SPJIP_A, "ForAlighting", "false")
        add_text(SPJIP_A, "ForBoarding", "true")
        FPP_A = ET.SubElement(SPJIP_A, n("FlexiblePointProperties"))
        if route[0] in gebiedscodes:
            add_text(FPP_A, "PointsStandingForAZone", 'true')
            add_text(FPP_A, "ZoneContainingStops", 'true')
        else:  
            add_text(FPP_A, "PointsStandingForAZone", 'false')

        SPJIP_B = ET.SubElement(pointsInSequence, n("StopPointInJourneyPattern"), {"id": f"NL:{cfg.codespace}:StopPointInJourneyPattern:{route[0]}_{route[1]}_2", "version": cfg.version})
        ET.SubElement(SPJIP_B, n("ScheduledStopPointRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ScheduledStopPoint:{route[1]}"})
        add_text(SPJIP_B, "ForAlighting", "true")
        add_text(SPJIP_B, "ForBoarding", "false")
        FPP_B = ET.SubElement(SPJIP_B, n("FlexiblePointProperties"))
        if route[1] in gebiedscodes:
            add_text(FPP_B, "PointsStandingForAZone", 'true')
            add_text(FPP_B, "ZoneContainingStops", 'true')
        else:  
            add_text(FPP_B, "PointsStandingForAZone", 'false')

        SJ = ET.SubElement(vehicle_journeys, n("ServiceJourney"), {"id": f"NL:{cfg.codespace}:ServiceJourney:{route[0]}_{route[1]}", "version": cfg.version})
        validityConditions = ET.SubElement(SJ, n("validityConditions"))
        for _, row in bdt.iterrows():      
            ET.SubElement(validityConditions, n("AvailabilityConditionRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:AvailabilityCondition:{row['code']}"})
        ET.SubElement(SJ, n("ServiceJourneyPatternRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:ServiceJourneyPattern:{route[0]}_{route[1]}"})
        ET.SubElement(SJ, n("FlexibleServicePropertiesRef"), {"version": cfg.version, "ref": f"NL:{cfg.codespace}:FlexibleServiceProperties:{cfg.frame_key}"})

    CVC = ET.SubElement(timetable, n("contentValidityConditions"))
    for _, row in bdt.iterrows():            
        AC = ET.SubElement(CVC, n("AvailabilityCondition"), {"id": f"NL:{cfg.codespace}:AvailabilityCondition:{row['code']}", "version": cfg.version})
        add_text(AC, "FromDate", cfg.valid_from)
        add_text(AC, "ToDate", cfg.valid_to)
        add_text(AC, "ValidDayBits", row['dagen'] * 52)  # Every day of the year
        timebands = ET.SubElement(AC, n("timebands"))
        timeband = ET.SubElement(timebands, n("Timeband"), {"id": f"NL:{cfg.codespace}:Timeband:{row['code']}", "version": cfg.version})
        add_text(timeband, "StartTime", row["start_time"])
        add_text(timeband, "EndTime", row["end_time"])
        if row["day_offset"] != 0:
            add_text(timeband, "DayOffset", str(row["day_offset"]))
    
    flexibleServiceProperties = ET.SubElement(timetable, n("flexibleServiceProperties"),{"id": f"NL:{cfg.codespace}:FlexibleServiceProperties:{cfg.frame_key}", "version": cfg.version})
    add_text(flexibleServiceProperties, "FlexibleServiceType", "dynamicPassingTimes")
    FSP_Ext = ET.SubElement(flexibleServiceProperties, n("Extensions"))
    add_text(FSP_Ext, "SafeDurationFactor", f"{cfg.safe_duration_factor}")
    add_text(FSP_Ext, "SafeDurationOffset", f"{cfg.safe_duration_offset}")  
    return ET.ElementTree(root)

def add_flexible_areas(tree: ET.ElementTree, flex_area: dict, cfg: ExportConfig) -> ET.ElementTree:
    resource_frame = tree.find(f".//{n('ResourceFrame')}")
    if resource_frame is None:
        return tree

    def remove_existing_flexible_area(area_id: str) -> None:
        for parent in tree.getroot().iter():
            for child in list(parent):
                if child.tag == n("FlexibleArea") and child.get("id") == area_id:
                    parent.remove(child)

    for area_name, coordinates in flex_area.items():
        area_id = f"NL:{cfg.codespace}:FlexibleArea:{area_name}"
        remove_existing_flexible_area(area_id)

        area = ET.Element(n("FlexibleArea"), {"id": area_id, "version": cfg.version})
        add_text(area, "Name", area_name)
        add_text(area, "ShortName", slugify(area_name))
        polygon = ET.SubElement(area, g("Polygon"), {g("id"): f"NL_{cfg.codespace}_FlexibleArea_{slugify(area_name)}"})
        exterior = ET.SubElement(polygon, g("exterior"))
        linear_ring = ET.SubElement(exterior, g("LinearRing"))
        pos_list = ET.SubElement(linear_ring, g("posList"))
        pos_list.text = coordinates
        add_text(area, "BoardingUse", "true")
        add_text(area, "AlightingUse", "true")
        resource_frame.append(area)

    return tree

def main() -> None:
    pass


if __name__ == "__main__":
    project = 'FlexRRReisFlevoland'
    config_path = Path(f'config_{project}.csv')
    flex_area_path = Path(f'flex_area_{project}.json')
    
    stops = read_stops(Path(f'stops_{project}.csv'))
    adresses = read_stops(Path(f'adresses_{project}.csv'))
    cfg = read_config(config_path)
    bdt = read_bedieningstijden(Path(f'bedieningstijden_{project}.csv'))
    flex_area = read_flex_area(flex_area_path)
    
    print('Read input data: {} stops, config with frame key {}, and {} bedieningstijden'.format(len(stops), cfg.frame_key, len(bdt)))
    tree_stops = build_xml(stops, cfg, bdt)
    ET.indent(tree_stops, space="    ")
    output_stops = Path(f'NeTEx_PFL_{project}_stops_{cfg.publication_timestamp.replace('-','')[0:8]}.xml')
    tree_stops.write(output_stops, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {len(stops)} stops records to {output_stops}")
    
    if not adresses.empty:
        print(f"Adding adresses from {adresses}")
        tree_adresses = build_xml(adresses, cfg, bdt)
        output_adresses = Path(f'NeTEx_PFL_{project}_adresses_{cfg.publication_timestamp.replace('-','')[0:8]}.xml')
        tree_adresses.write(output_adresses, encoding="utf-8", xml_declaration=True)

    if flex_area:
        print(f"Adding flexible areas from {flex_area_path}")
        tree = add_flexible_areas(tree_stops, flex_area, cfg)
        output_path = Path(f'NeTEx_PFL_{project}_area_{cfg.publication_timestamp.replace('-','')[0:8]}.xml')
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

    
