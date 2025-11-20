--
-- PostgreSQL database dump
--

\restrict vS2jflO7aJRaeVgKgHPrlJV5lTBdMySFOYnZp2Mf2CUzduvwtCLFscdwqbzrF91

-- Dumped from database version 16.9 (415ebe8)
-- Dumped by pg_dump version 16.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bundle_components; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bundle_components (
    id integer NOT NULL,
    bundle_sku_id integer NOT NULL,
    component_sku text NOT NULL,
    multiplier integer NOT NULL,
    sequence integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bundle_components_multiplier_check CHECK ((multiplier > 0))
);


--
-- Name: bundle_components_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bundle_components_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bundle_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bundle_components_id_seq OWNED BY public.bundle_components.id;


--
-- Name: bundle_skus; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bundle_skus (
    id integer NOT NULL,
    bundle_sku text NOT NULL,
    description text NOT NULL,
    active integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    updated_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT bundle_skus_active_check CHECK ((active = ANY (ARRAY[0, 1])))
);


--
-- Name: bundle_skus_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bundle_skus_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bundle_skus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bundle_skus_id_seq OWNED BY public.bundle_skus.id;


--
-- Name: configuration_params; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuration_params (
    id integer NOT NULL,
    category text NOT NULL,
    parameter_name text NOT NULL,
    value text NOT NULL,
    sku text,
    notes text,
    last_updated text,
    created_at text DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: configuration_params_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.configuration_params_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: configuration_params_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.configuration_params_id_seq OWNED BY public.configuration_params.id;


--
-- Name: deleted_shipstation_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deleted_shipstation_orders (
    id integer NOT NULL,
    shipstation_order_id bigint NOT NULL,
    order_number character varying(50),
    deleted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_by character varying(100) DEFAULT 'dashboard'::character varying
);


--
-- Name: deleted_shipstation_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.deleted_shipstation_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deleted_shipstation_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.deleted_shipstation_orders_id_seq OWNED BY public.deleted_shipstation_orders.id;


--
-- Name: duplicate_order_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.duplicate_order_alerts (
    id integer NOT NULL,
    order_number text NOT NULL,
    duplicate_count integer NOT NULL,
    shipstation_ids text NOT NULL,
    first_detected timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_seen timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    status text DEFAULT 'active'::text,
    details text,
    resolved_at timestamp without time zone,
    resolved_by text,
    notes text,
    base_sku character varying(50),
    resolution_notes text,
    CONSTRAINT duplicate_order_alerts_status_check CHECK ((status = ANY (ARRAY['active'::text, 'resolved'::text, 'ignored'::text])))
);


--
-- Name: duplicate_order_alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.duplicate_order_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: duplicate_order_alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.duplicate_order_alerts_id_seq OWNED BY public.duplicate_order_alerts.id;


--
-- Name: email_contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_contacts (
    id integer NOT NULL,
    email text NOT NULL,
    name text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: email_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.email_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.email_contacts_id_seq OWNED BY public.email_contacts.id;


--
-- Name: excluded_duplicate_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.excluded_duplicate_orders (
    id integer NOT NULL,
    order_number character varying(100) NOT NULL,
    base_sku character varying(50) NOT NULL,
    excluded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    excluded_by character varying(100) DEFAULT 'manual'::character varying,
    exclusion_reason text
);


--
-- Name: excluded_duplicate_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.excluded_duplicate_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: excluded_duplicate_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.excluded_duplicate_orders_id_seq OWNED BY public.excluded_duplicate_orders.id;


--
-- Name: fedex_pickup_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fedex_pickup_log (
    id integer NOT NULL,
    pickup_date date NOT NULL,
    units_count integer NOT NULL,
    completed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_by text,
    notes text
);


--
-- Name: fedex_pickup_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.fedex_pickup_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fedex_pickup_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.fedex_pickup_log_id_seq OWNED BY public.fedex_pickup_log.id;


--
-- Name: incident_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.incident_notes (
    id integer NOT NULL,
    incident_id integer NOT NULL,
    note_type character varying(20) NOT NULL,
    note text NOT NULL,
    created_by character varying(255) DEFAULT 'System'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT incident_notes_note_type_check CHECK (((note_type)::text = ANY ((ARRAY['user'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: incident_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.incident_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: incident_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.incident_notes_id_seq OWNED BY public.incident_notes.id;


--
-- Name: inventory_current; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_current (
    id integer NOT NULL,
    sku text NOT NULL,
    product_name text,
    current_quantity integer NOT NULL,
    weekly_avg_cents integer,
    alert_level text DEFAULT 'normal'::text NOT NULL,
    reorder_point integer DEFAULT 50 NOT NULL,
    last_updated text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inventory_current_alert_level_check CHECK ((alert_level = ANY (ARRAY['normal'::text, 'low'::text, 'critical'::text])))
);


--
-- Name: inventory_current_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_current_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_current_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventory_current_id_seq OWNED BY public.inventory_current.id;


--
-- Name: inventory_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_transactions (
    id integer NOT NULL,
    date text NOT NULL,
    sku text NOT NULL,
    quantity integer NOT NULL,
    transaction_type text NOT NULL,
    notes text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inventory_transactions_quantity_check CHECK ((quantity <> 0)),
    CONSTRAINT inventory_transactions_transaction_type_check CHECK ((transaction_type = ANY (ARRAY['Receive'::text, 'Ship'::text, 'Adjust Up'::text, 'Adjust Down'::text, 'Repack'::text])))
);


--
-- Name: inventory_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inventory_transactions_id_seq OWNED BY public.inventory_transactions.id;


--
-- Name: lot_inventory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lot_inventory (
    id integer NOT NULL,
    sku text NOT NULL,
    lot text NOT NULL,
    initial_qty integer DEFAULT 0 NOT NULL,
    manual_adjustment integer DEFAULT 0 NOT NULL,
    received_date text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    notes text,
    created_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: lot_inventory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lot_inventory_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lot_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lot_inventory_id_seq OWNED BY public.lot_inventory.id;


--
-- Name: lot_mismatch_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lot_mismatch_alerts (
    id integer NOT NULL,
    order_number character varying(50) NOT NULL,
    base_sku character varying(50) NOT NULL,
    shipstation_lot character varying(100),
    active_lot character varying(100) NOT NULL,
    shipstation_order_id character varying(50),
    shipstation_item_id character varying(50),
    order_status character varying(50),
    detected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    resolved_at timestamp without time zone,
    resolved_by character varying(100)
);


--
-- Name: lot_mismatch_alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lot_mismatch_alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lot_mismatch_alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lot_mismatch_alerts_id_seq OWNED BY public.lot_mismatch_alerts.id;


--
-- Name: manual_order_conflicts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.manual_order_conflicts (
    id integer NOT NULL,
    conflicting_order_number character varying(50) NOT NULL,
    shipstation_order_id character varying(50) NOT NULL,
    customer_name character varying(255),
    original_ship_date timestamp without time zone,
    detected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    resolved_at timestamp without time zone,
    new_order_number character varying(50),
    new_shipstation_order_id character varying(50),
    resolution_status character varying(50) DEFAULT 'pending'::character varying,
    original_company character varying(255),
    original_items jsonb,
    duplicate_company character varying(255),
    duplicate_items jsonb
);


--
-- Name: manual_order_conflicts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.manual_order_conflicts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: manual_order_conflicts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.manual_order_conflicts_id_seq OWNED BY public.manual_order_conflicts.id;


--
-- Name: oauth; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth (
    id integer NOT NULL,
    provider character varying NOT NULL,
    provider_user_id character varying,
    token text,
    user_id character varying,
    browser_session_key character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: oauth_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.oauth_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oauth_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.oauth_id_seq OWNED BY public.oauth.id;


--
-- Name: order_items_inbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items_inbox (
    id integer NOT NULL,
    order_inbox_id integer NOT NULL,
    sku text NOT NULL,
    sku_lot text,
    quantity integer NOT NULL,
    unit_price_cents integer,
    CONSTRAINT order_items_inbox_quantity_check CHECK ((quantity > 0))
);


--
-- Name: order_items_inbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.order_items_inbox_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_items_inbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.order_items_inbox_id_seq OWNED BY public.order_items_inbox.id;


--
-- Name: orders_inbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders_inbox (
    id integer NOT NULL,
    order_number text NOT NULL,
    order_date date NOT NULL,
    customer_email text,
    status text DEFAULT 'pending'::text NOT NULL,
    shipstation_order_id text,
    total_items integer DEFAULT 0,
    total_amount_cents integer,
    source_system text DEFAULT 'X-Cart'::text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    failure_reason text,
    ship_name text,
    ship_company text,
    ship_street1 text,
    ship_street2 text,
    ship_city text,
    ship_state text,
    ship_postal_code text,
    ship_country text,
    ship_phone text,
    bill_name text,
    bill_company text,
    bill_street1 text,
    bill_street2 text,
    bill_city text,
    bill_state text,
    bill_postal_code text,
    bill_country text,
    bill_phone text,
    shipping_carrier_code text,
    shipping_carrier_id text,
    shipping_service_code text,
    shipping_service_name text,
    tracking_number text,
    is_flagged boolean DEFAULT false,
    flag_reason character varying(200),
    notes text,
    flagged_at timestamp without time zone,
    tracking_status character varying(10),
    tracking_status_description text,
    exception_description text,
    tracking_last_checked timestamp without time zone,
    tracking_last_updated timestamp without time zone,
    flag_resolved boolean DEFAULT false,
    flag_resolved_at timestamp without time zone,
    flag_resolved_by character varying(255),
    CONSTRAINT orders_inbox_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'uploaded'::text, 'awaiting_shipment'::text, 'failed'::text, 'synced_manual'::text, 'shipped'::text, 'cancelled'::text, 'on_hold'::text, 'awaiting_payment'::text])))
);


--
-- Name: orders_inbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.orders_inbox_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_inbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.orders_inbox_id_seq OWNED BY public.orders_inbox.id;


--
-- Name: polling_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.polling_state (
    id integer DEFAULT 1 NOT NULL,
    last_upload_count integer DEFAULT 0,
    last_upload_check timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_xml_count text DEFAULT 0,
    last_xml_check timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_row CHECK ((id = 1))
);


--
-- Name: production_incident_screenshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production_incident_screenshots (
    id integer NOT NULL,
    incident_id integer NOT NULL,
    file_path character varying(500) NOT NULL,
    original_filename character varying(255) NOT NULL,
    file_size integer,
    uploaded_by character varying(255) DEFAULT 'Dashboard User'::character varying,
    uploaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: production_incident_screenshots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.production_incident_screenshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: production_incident_screenshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.production_incident_screenshots_id_seq OWNED BY public.production_incident_screenshots.id;


--
-- Name: production_incidents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production_incidents (
    id integer NOT NULL,
    title character varying(500) NOT NULL,
    description text NOT NULL,
    severity character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'new'::character varying NOT NULL,
    reported_by character varying(255) DEFAULT 'Dashboard User'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    cause text,
    resolution text,
    CONSTRAINT production_incidents_severity_check CHECK (((severity)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT production_incidents_status_check CHECK (((status)::text = ANY ((ARRAY['new'::character varying, 'in_progress'::character varying, 'resolved'::character varying, 'closed'::character varying])::text[])))
);


--
-- Name: production_incidents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.production_incidents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: production_incidents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.production_incidents_id_seq OWNED BY public.production_incidents.id;


--
-- Name: report_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_runs (
    id integer NOT NULL,
    report_type character varying(10) NOT NULL,
    run_date date NOT NULL,
    run_for_date date NOT NULL,
    status character varying(20) NOT NULL,
    message text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: report_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.report_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: report_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.report_runs_id_seq OWNED BY public.report_runs.id;


--
-- Name: shipped_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipped_items (
    id integer NOT NULL,
    ship_date text NOT NULL,
    sku_lot text DEFAULT ''::text NOT NULL,
    base_sku text NOT NULL,
    quantity_shipped integer NOT NULL,
    order_number text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    tracking_number text,
    CONSTRAINT shipped_items_quantity_shipped_check CHECK ((quantity_shipped > 0))
);


--
-- Name: shipped_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipped_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipped_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipped_items_id_seq OWNED BY public.shipped_items.id;


--
-- Name: shipped_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipped_orders (
    id integer NOT NULL,
    ship_date text NOT NULL,
    order_number text NOT NULL,
    customer_email text,
    total_items integer DEFAULT 0,
    shipstation_order_id text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    shipping_carrier_code text,
    shipping_carrier_id text,
    shipping_service_code text,
    shipping_service_name text
);


--
-- Name: shipped_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipped_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipped_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipped_orders_id_seq OWNED BY public.shipped_orders.id;


--
-- Name: shipping_violations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipping_violations (
    id integer NOT NULL,
    order_id integer NOT NULL,
    order_number text NOT NULL,
    violation_type text NOT NULL,
    expected_value text NOT NULL,
    actual_value text,
    detected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    resolved_at timestamp without time zone,
    is_resolved integer DEFAULT 0 NOT NULL,
    CONSTRAINT shipping_violations_is_resolved_check CHECK ((is_resolved = ANY (ARRAY[0, 1]))),
    CONSTRAINT shipping_violations_violation_type_check CHECK ((violation_type = ANY (ARRAY['hawaiian_service'::text, 'benco_carrier'::text, 'canadian_service'::text])))
);


--
-- Name: shipping_violations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipping_violations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipping_violations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipping_violations_id_seq OWNED BY public.shipping_violations.id;


--
-- Name: shipstation_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipstation_metrics (
    id integer NOT NULL,
    metric_name text NOT NULL,
    metric_value integer NOT NULL,
    last_updated text DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: shipstation_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipstation_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipstation_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipstation_metrics_id_seq OWNED BY public.shipstation_metrics.id;


--
-- Name: shipstation_order_line_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shipstation_order_line_items (
    id integer NOT NULL,
    order_inbox_id integer NOT NULL,
    sku text NOT NULL,
    shipstation_order_id text NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: shipstation_order_line_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shipstation_order_line_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipstation_order_line_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shipstation_order_line_items_id_seq OWNED BY public.shipstation_order_line_items.id;


--
-- Name: sku_lot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sku_lot (
    id integer NOT NULL,
    sku text NOT NULL,
    lot text NOT NULL,
    active integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT sku_lot_active_check CHECK ((active = ANY (ARRAY[0, 1])))
);


--
-- Name: sku_lot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sku_lot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sku_lot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sku_lot_id_seq OWNED BY public.sku_lot.id;


--
-- Name: sync_watermark; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_watermark (
    id integer NOT NULL,
    workflow_name text NOT NULL,
    last_sync_timestamp text NOT NULL,
    updated_at text DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: sync_watermark_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sync_watermark_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sync_watermark_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sync_watermark_id_seq OWNED BY public.sync_watermark.id;


--
-- Name: system_kpis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_kpis (
    id integer NOT NULL,
    snapshot_date text NOT NULL,
    orders_today integer DEFAULT 0,
    shipments_sent integer DEFAULT 0,
    pending_uploads integer DEFAULT 0,
    system_status text DEFAULT 'online'::text NOT NULL,
    total_revenue_cents integer,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT system_kpis_system_status_check CHECK ((system_status = ANY (ARRAY['online'::text, 'degraded'::text, 'offline'::text])))
);


--
-- Name: system_kpis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.system_kpis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: system_kpis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.system_kpis_id_seq OWNED BY public.system_kpis.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying NOT NULL,
    email character varying,
    first_name character varying,
    last_name character varying,
    profile_image_url text,
    role character varying DEFAULT 'viewer'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: weekly_shipped_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.weekly_shipped_history (
    id integer NOT NULL,
    start_date text NOT NULL,
    end_date text NOT NULL,
    sku text NOT NULL,
    quantity_shipped integer NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT weekly_shipped_history_quantity_shipped_check CHECK ((quantity_shipped >= 0))
);


--
-- Name: weekly_shipped_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.weekly_shipped_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: weekly_shipped_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.weekly_shipped_history_id_seq OWNED BY public.weekly_shipped_history.id;


--
-- Name: workflow_controls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_controls (
    workflow_name text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by text DEFAULT 'system'::text,
    last_run_at timestamp without time zone
);


--
-- Name: workflows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflows (
    id integer NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    status text NOT NULL,
    last_run_at timestamp with time zone,
    duration_seconds integer,
    records_processed integer,
    details text,
    enabled integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT workflows_enabled_check CHECK ((enabled = ANY (ARRAY[0, 1]))),
    CONSTRAINT workflows_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'scheduled'::text])))
);


--
-- Name: workflows_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.workflows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workflows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.workflows_id_seq OWNED BY public.workflows.id;


--
-- Name: bundle_components id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_components ALTER COLUMN id SET DEFAULT nextval('public.bundle_components_id_seq'::regclass);


--
-- Name: bundle_skus id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_skus ALTER COLUMN id SET DEFAULT nextval('public.bundle_skus_id_seq'::regclass);


--
-- Name: configuration_params id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuration_params ALTER COLUMN id SET DEFAULT nextval('public.configuration_params_id_seq'::regclass);


--
-- Name: deleted_shipstation_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deleted_shipstation_orders ALTER COLUMN id SET DEFAULT nextval('public.deleted_shipstation_orders_id_seq'::regclass);


--
-- Name: duplicate_order_alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_order_alerts ALTER COLUMN id SET DEFAULT nextval('public.duplicate_order_alerts_id_seq'::regclass);


--
-- Name: email_contacts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_contacts ALTER COLUMN id SET DEFAULT nextval('public.email_contacts_id_seq'::regclass);


--
-- Name: excluded_duplicate_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.excluded_duplicate_orders ALTER COLUMN id SET DEFAULT nextval('public.excluded_duplicate_orders_id_seq'::regclass);


--
-- Name: fedex_pickup_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fedex_pickup_log ALTER COLUMN id SET DEFAULT nextval('public.fedex_pickup_log_id_seq'::regclass);


--
-- Name: incident_notes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_notes ALTER COLUMN id SET DEFAULT nextval('public.incident_notes_id_seq'::regclass);


--
-- Name: inventory_current id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_current ALTER COLUMN id SET DEFAULT nextval('public.inventory_current_id_seq'::regclass);


--
-- Name: inventory_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions ALTER COLUMN id SET DEFAULT nextval('public.inventory_transactions_id_seq'::regclass);


--
-- Name: lot_inventory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_inventory ALTER COLUMN id SET DEFAULT nextval('public.lot_inventory_id_seq'::regclass);


--
-- Name: lot_mismatch_alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_mismatch_alerts ALTER COLUMN id SET DEFAULT nextval('public.lot_mismatch_alerts_id_seq'::regclass);


--
-- Name: manual_order_conflicts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manual_order_conflicts ALTER COLUMN id SET DEFAULT nextval('public.manual_order_conflicts_id_seq'::regclass);


--
-- Name: oauth id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth ALTER COLUMN id SET DEFAULT nextval('public.oauth_id_seq'::regclass);


--
-- Name: order_items_inbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox ALTER COLUMN id SET DEFAULT nextval('public.order_items_inbox_id_seq'::regclass);


--
-- Name: orders_inbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders_inbox ALTER COLUMN id SET DEFAULT nextval('public.orders_inbox_id_seq'::regclass);


--
-- Name: production_incident_screenshots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_incident_screenshots ALTER COLUMN id SET DEFAULT nextval('public.production_incident_screenshots_id_seq'::regclass);


--
-- Name: production_incidents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_incidents ALTER COLUMN id SET DEFAULT nextval('public.production_incidents_id_seq'::regclass);


--
-- Name: report_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_runs ALTER COLUMN id SET DEFAULT nextval('public.report_runs_id_seq'::regclass);


--
-- Name: shipped_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_items ALTER COLUMN id SET DEFAULT nextval('public.shipped_items_id_seq'::regclass);


--
-- Name: shipped_orders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_orders ALTER COLUMN id SET DEFAULT nextval('public.shipped_orders_id_seq'::regclass);


--
-- Name: shipping_violations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_violations ALTER COLUMN id SET DEFAULT nextval('public.shipping_violations_id_seq'::regclass);


--
-- Name: shipstation_metrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_metrics ALTER COLUMN id SET DEFAULT nextval('public.shipstation_metrics_id_seq'::regclass);


--
-- Name: shipstation_order_line_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_order_line_items ALTER COLUMN id SET DEFAULT nextval('public.shipstation_order_line_items_id_seq'::regclass);


--
-- Name: sku_lot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sku_lot ALTER COLUMN id SET DEFAULT nextval('public.sku_lot_id_seq'::regclass);


--
-- Name: sync_watermark id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_watermark ALTER COLUMN id SET DEFAULT nextval('public.sync_watermark_id_seq'::regclass);


--
-- Name: system_kpis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_kpis ALTER COLUMN id SET DEFAULT nextval('public.system_kpis_id_seq'::regclass);


--
-- Name: weekly_shipped_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_shipped_history ALTER COLUMN id SET DEFAULT nextval('public.weekly_shipped_history_id_seq'::regclass);


--
-- Name: workflows id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows ALTER COLUMN id SET DEFAULT nextval('public.workflows_id_seq'::regclass);


--
-- Name: bundle_components bundle_components_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_components
    ADD CONSTRAINT bundle_components_pkey PRIMARY KEY (id);


--
-- Name: bundle_skus bundle_skus_bundle_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_skus
    ADD CONSTRAINT bundle_skus_bundle_sku_key UNIQUE (bundle_sku);


--
-- Name: bundle_skus bundle_skus_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_skus
    ADD CONSTRAINT bundle_skus_pkey PRIMARY KEY (id);


--
-- Name: configuration_params configuration_params_category_parameter_name_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuration_params
    ADD CONSTRAINT configuration_params_category_parameter_name_sku_key UNIQUE (category, parameter_name, sku);


--
-- Name: configuration_params configuration_params_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuration_params
    ADD CONSTRAINT configuration_params_pkey PRIMARY KEY (id);


--
-- Name: deleted_shipstation_orders deleted_shipstation_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deleted_shipstation_orders
    ADD CONSTRAINT deleted_shipstation_orders_pkey PRIMARY KEY (id);


--
-- Name: deleted_shipstation_orders deleted_shipstation_orders_shipstation_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deleted_shipstation_orders
    ADD CONSTRAINT deleted_shipstation_orders_shipstation_order_id_key UNIQUE (shipstation_order_id);


--
-- Name: duplicate_order_alerts duplicate_order_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_order_alerts
    ADD CONSTRAINT duplicate_order_alerts_pkey PRIMARY KEY (id);


--
-- Name: email_contacts email_contacts_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_contacts
    ADD CONSTRAINT email_contacts_email_key UNIQUE (email);


--
-- Name: email_contacts email_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_contacts
    ADD CONSTRAINT email_contacts_pkey PRIMARY KEY (id);


--
-- Name: excluded_duplicate_orders excluded_duplicate_orders_order_number_base_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.excluded_duplicate_orders
    ADD CONSTRAINT excluded_duplicate_orders_order_number_base_sku_key UNIQUE (order_number, base_sku);


--
-- Name: excluded_duplicate_orders excluded_duplicate_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.excluded_duplicate_orders
    ADD CONSTRAINT excluded_duplicate_orders_pkey PRIMARY KEY (id);


--
-- Name: fedex_pickup_log fedex_pickup_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fedex_pickup_log
    ADD CONSTRAINT fedex_pickup_log_pkey PRIMARY KEY (id);


--
-- Name: incident_notes incident_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_notes
    ADD CONSTRAINT incident_notes_pkey PRIMARY KEY (id);


--
-- Name: inventory_current inventory_current_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_current
    ADD CONSTRAINT inventory_current_pkey PRIMARY KEY (id);


--
-- Name: inventory_current inventory_current_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_current
    ADD CONSTRAINT inventory_current_sku_key UNIQUE (sku);


--
-- Name: inventory_transactions inventory_transactions_date_sku_transaction_type_quantity_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_date_sku_transaction_type_quantity_key UNIQUE (date, sku, transaction_type, quantity);


--
-- Name: inventory_transactions inventory_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_transactions
    ADD CONSTRAINT inventory_transactions_pkey PRIMARY KEY (id);


--
-- Name: lot_inventory lot_inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_inventory
    ADD CONSTRAINT lot_inventory_pkey PRIMARY KEY (id);


--
-- Name: lot_inventory lot_inventory_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_inventory
    ADD CONSTRAINT lot_inventory_sku_lot_key UNIQUE (sku, lot);


--
-- Name: lot_mismatch_alerts lot_mismatch_alerts_order_number_base_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_mismatch_alerts
    ADD CONSTRAINT lot_mismatch_alerts_order_number_base_sku_key UNIQUE (order_number, base_sku);


--
-- Name: lot_mismatch_alerts lot_mismatch_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lot_mismatch_alerts
    ADD CONSTRAINT lot_mismatch_alerts_pkey PRIMARY KEY (id);


--
-- Name: manual_order_conflicts manual_order_conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manual_order_conflicts
    ADD CONSTRAINT manual_order_conflicts_pkey PRIMARY KEY (id);


--
-- Name: manual_order_conflicts manual_order_conflicts_shipstation_order_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manual_order_conflicts
    ADD CONSTRAINT manual_order_conflicts_shipstation_order_id_key UNIQUE (shipstation_order_id);


--
-- Name: oauth oauth_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT oauth_pkey PRIMARY KEY (id);


--
-- Name: order_items_inbox order_items_inbox_order_sku_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_order_sku_unique UNIQUE (order_inbox_id, sku);


--
-- Name: order_items_inbox order_items_inbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_pkey PRIMARY KEY (id);


--
-- Name: orders_inbox orders_inbox_order_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders_inbox
    ADD CONSTRAINT orders_inbox_order_number_key UNIQUE (order_number);


--
-- Name: orders_inbox orders_inbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders_inbox
    ADD CONSTRAINT orders_inbox_pkey PRIMARY KEY (id);


--
-- Name: polling_state polling_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.polling_state
    ADD CONSTRAINT polling_state_pkey PRIMARY KEY (id);


--
-- Name: production_incident_screenshots production_incident_screenshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_incident_screenshots
    ADD CONSTRAINT production_incident_screenshots_pkey PRIMARY KEY (id);


--
-- Name: production_incidents production_incidents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_incidents
    ADD CONSTRAINT production_incidents_pkey PRIMARY KEY (id);


--
-- Name: report_runs report_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_runs
    ADD CONSTRAINT report_runs_pkey PRIMARY KEY (id);


--
-- Name: report_runs report_runs_report_type_run_for_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_runs
    ADD CONSTRAINT report_runs_report_type_run_for_date_key UNIQUE (report_type, run_for_date);


--
-- Name: shipped_items shipped_items_order_number_base_sku_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_order_number_base_sku_sku_lot_key UNIQUE (order_number, base_sku, sku_lot);


--
-- Name: shipped_items shipped_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_pkey PRIMARY KEY (id);


--
-- Name: shipped_orders shipped_orders_order_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_orders
    ADD CONSTRAINT shipped_orders_order_number_key UNIQUE (order_number);


--
-- Name: shipped_orders shipped_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_orders
    ADD CONSTRAINT shipped_orders_pkey PRIMARY KEY (id);


--
-- Name: shipping_violations shipping_violations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_violations
    ADD CONSTRAINT shipping_violations_pkey PRIMARY KEY (id);


--
-- Name: shipstation_metrics shipstation_metrics_metric_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_metrics
    ADD CONSTRAINT shipstation_metrics_metric_name_key UNIQUE (metric_name);


--
-- Name: shipstation_metrics shipstation_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_metrics
    ADD CONSTRAINT shipstation_metrics_pkey PRIMARY KEY (id);


--
-- Name: shipstation_order_line_items shipstation_order_line_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_order_line_items
    ADD CONSTRAINT shipstation_order_line_items_pkey PRIMARY KEY (id);


--
-- Name: sku_lot sku_lot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sku_lot
    ADD CONSTRAINT sku_lot_pkey PRIMARY KEY (id);


--
-- Name: sku_lot sku_lot_sku_lot_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sku_lot
    ADD CONSTRAINT sku_lot_sku_lot_key UNIQUE (sku, lot);


--
-- Name: sync_watermark sync_watermark_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_watermark
    ADD CONSTRAINT sync_watermark_pkey PRIMARY KEY (id);


--
-- Name: sync_watermark sync_watermark_workflow_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_watermark
    ADD CONSTRAINT sync_watermark_workflow_name_key UNIQUE (workflow_name);


--
-- Name: system_kpis system_kpis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_kpis
    ADD CONSTRAINT system_kpis_pkey PRIMARY KEY (id);


--
-- Name: system_kpis system_kpis_snapshot_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_kpis
    ADD CONSTRAINT system_kpis_snapshot_date_key UNIQUE (snapshot_date);


--
-- Name: oauth uq_user_browser_session_key_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT uq_user_browser_session_key_provider UNIQUE (user_id, browser_session_key, provider);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: weekly_shipped_history weekly_shipped_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_shipped_history
    ADD CONSTRAINT weekly_shipped_history_pkey PRIMARY KEY (id);


--
-- Name: weekly_shipped_history weekly_shipped_history_start_date_end_date_sku_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_shipped_history
    ADD CONSTRAINT weekly_shipped_history_start_date_end_date_sku_key UNIQUE (start_date, end_date, sku);


--
-- Name: workflow_controls workflow_controls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_controls
    ADD CONSTRAINT workflow_controls_pkey PRIMARY KEY (workflow_name);


--
-- Name: workflows workflows_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_name_key UNIQUE (name);


--
-- Name: workflows workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows
    ADD CONSTRAINT workflows_pkey PRIMARY KEY (id);


--
-- Name: duplicate_order_alerts_active_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX duplicate_order_alerts_active_unique ON public.duplicate_order_alerts USING btree (order_number, base_sku) WHERE (status = 'active'::text);


--
-- Name: duplicate_order_alerts_unique_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX duplicate_order_alerts_unique_active ON public.duplicate_order_alerts USING btree (order_number, base_sku, status) WHERE (status = 'active'::text);


--
-- Name: idx_bundle_components_bundle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bundle_components_bundle ON public.bundle_components USING btree (bundle_sku_id);


--
-- Name: idx_bundle_components_sku; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bundle_components_sku ON public.bundle_components USING btree (component_sku);


--
-- Name: idx_bundle_skus_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bundle_skus_active ON public.bundle_skus USING btree (active);


--
-- Name: idx_config_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_config_category ON public.configuration_params USING btree (category);


--
-- Name: idx_config_sku; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_config_sku ON public.configuration_params USING btree (sku);


--
-- Name: idx_deleted_ss_orders_ss_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_deleted_ss_orders_ss_id ON public.deleted_shipstation_orders USING btree (shipstation_order_id);


--
-- Name: idx_duplicate_alerts_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_alerts_order ON public.duplicate_order_alerts USING btree (order_number);


--
-- Name: idx_duplicate_alerts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_alerts_status ON public.duplicate_order_alerts USING btree (status, last_seen DESC);


--
-- Name: idx_excluded_orders_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_excluded_orders_lookup ON public.excluded_duplicate_orders USING btree (order_number, base_sku);


--
-- Name: idx_incident_notes_incident_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_incident_notes_incident_id ON public.incident_notes USING btree (incident_id);


--
-- Name: idx_incidents_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_incidents_severity ON public.production_incidents USING btree (severity);


--
-- Name: idx_incidents_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_incidents_status ON public.production_incidents USING btree (status);


--
-- Name: idx_inv_trans_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inv_trans_date ON public.inventory_transactions USING btree (date);


--
-- Name: idx_inv_trans_sku_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inv_trans_sku_date ON public.inventory_transactions USING btree (sku, date);


--
-- Name: idx_inv_trans_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inv_trans_type ON public.inventory_transactions USING btree (transaction_type);


--
-- Name: idx_inventory_current_alert; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inventory_current_alert ON public.inventory_current USING btree (alert_level);


--
-- Name: idx_lot_mismatch_alerts_unresolved; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lot_mismatch_alerts_unresolved ON public.lot_mismatch_alerts USING btree (order_number, base_sku) WHERE (resolved_at IS NULL);


--
-- Name: idx_oauth_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oauth_user_id ON public.oauth USING btree (user_id);


--
-- Name: idx_order_items_inbox_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_inbox_order ON public.order_items_inbox USING btree (order_inbox_id);


--
-- Name: idx_order_items_inbox_sku; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_inbox_sku ON public.order_items_inbox USING btree (sku);


--
-- Name: idx_orders_inbox_awaiting; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_inbox_awaiting ON public.orders_inbox USING btree (status) WHERE (status = 'awaiting_shipment'::text);


--
-- Name: idx_orders_inbox_flagged; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_inbox_flagged ON public.orders_inbox USING btree (is_flagged);


--
-- Name: idx_orders_tracking_last_checked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_tracking_last_checked ON public.orders_inbox USING btree (tracking_last_checked) WHERE ((tracking_number IS NOT NULL) AND (tracking_number <> ''::text));


--
-- Name: idx_orders_tracking_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_tracking_status ON public.orders_inbox USING btree (tracking_status) WHERE (tracking_status IS NOT NULL);


--
-- Name: idx_screenshots_incident; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_screenshots_incident ON public.production_incident_screenshots USING btree (incident_id);


--
-- Name: idx_shipped_items_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipped_items_date ON public.shipped_items USING btree (ship_date);


--
-- Name: idx_shipped_items_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipped_items_order ON public.shipped_items USING btree (order_number);


--
-- Name: idx_shipped_items_sku_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipped_items_sku_date ON public.shipped_items USING btree (base_sku, ship_date);


--
-- Name: idx_shipped_orders_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shipped_orders_date ON public.shipped_orders USING btree (ship_date);


--
-- Name: idx_shipstation_order_line_items_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique ON public.shipstation_order_line_items USING btree (order_inbox_id, sku);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_violations_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_violations_order ON public.shipping_violations USING btree (order_id);


--
-- Name: idx_violations_resolved; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_violations_resolved ON public.shipping_violations USING btree (is_resolved, detected_at);


--
-- Name: idx_violations_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_violations_type ON public.shipping_violations USING btree (violation_type);


--
-- Name: idx_weekly_history_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_weekly_history_dates ON public.weekly_shipped_history USING btree (start_date, end_date);


--
-- Name: idx_weekly_history_sku_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_weekly_history_sku_start ON public.weekly_shipped_history USING btree (sku, start_date);


--
-- Name: idx_workflows_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflows_enabled ON public.workflows USING btree (enabled);


--
-- Name: idx_workflows_last_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflows_last_run ON public.workflows USING btree (status, last_run_at);


--
-- Name: idx_workflows_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflows_status ON public.workflows USING btree (status, enabled);


--
-- Name: uniq_shipped_items_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uniq_shipped_items_key ON public.shipped_items USING btree (order_number, base_sku, sku_lot);


--
-- Name: workflows update_workflows_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON public.workflows FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: bundle_components bundle_components_bundle_sku_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_components
    ADD CONSTRAINT bundle_components_bundle_sku_id_fkey FOREIGN KEY (bundle_sku_id) REFERENCES public.bundle_skus(id) ON DELETE CASCADE;


--
-- Name: incident_notes incident_notes_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.incident_notes
    ADD CONSTRAINT incident_notes_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.production_incidents(id) ON DELETE CASCADE;


--
-- Name: oauth oauth_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT oauth_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: order_items_inbox order_items_inbox_order_inbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_order_inbox_id_fkey FOREIGN KEY (order_inbox_id) REFERENCES public.orders_inbox(id) ON DELETE CASCADE;


--
-- Name: production_incident_screenshots production_incident_screenshots_incident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_incident_screenshots
    ADD CONSTRAINT production_incident_screenshots_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES public.production_incidents(id) ON DELETE CASCADE;


--
-- Name: shipped_items shipped_items_order_number_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipped_items
    ADD CONSTRAINT shipped_items_order_number_fkey FOREIGN KEY (order_number) REFERENCES public.shipped_orders(order_number);


--
-- Name: shipping_violations shipping_violations_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipping_violations
    ADD CONSTRAINT shipping_violations_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders_inbox(id) ON DELETE CASCADE;


--
-- Name: shipstation_order_line_items shipstation_order_line_items_order_inbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shipstation_order_line_items
    ADD CONSTRAINT shipstation_order_line_items_order_inbox_id_fkey FOREIGN KEY (order_inbox_id) REFERENCES public.orders_inbox(id);


--
-- PostgreSQL database dump complete
--

\unrestrict vS2jflO7aJRaeVgKgHPrlJV5lTBdMySFOYnZp2Mf2CUzduvwtCLFscdwqbzrF91

