--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (165f042)
-- Dumped by pg_dump version 16.9

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
-- Name: inventory_current; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_current (
    id integer NOT NULL,
    sku text NOT NULL,
    product_name text NOT NULL,
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
    last_run_at text,
    duration_seconds integer,
    records_processed integer,
    details text,
    enabled integer DEFAULT 1 NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    updated_at text DEFAULT CURRENT_TIMESTAMP,
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
-- Name: order_items_inbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox ALTER COLUMN id SET DEFAULT nextval('public.order_items_inbox_id_seq'::regclass);


--
-- Name: orders_inbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders_inbox ALTER COLUMN id SET DEFAULT nextval('public.orders_inbox_id_seq'::regclass);


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
-- Name: bundle_components bundle_components_bundle_sku_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bundle_components
    ADD CONSTRAINT bundle_components_bundle_sku_id_fkey FOREIGN KEY (bundle_sku_id) REFERENCES public.bundle_skus(id) ON DELETE CASCADE;


--
-- Name: order_items_inbox order_items_inbox_order_inbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items_inbox
    ADD CONSTRAINT order_items_inbox_order_inbox_id_fkey FOREIGN KEY (order_inbox_id) REFERENCES public.orders_inbox(id) ON DELETE CASCADE;


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

