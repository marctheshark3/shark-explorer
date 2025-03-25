-- Token holders tracking schema
-- This script creates tables and functions for tracking token balances by address

-- Table to store current token balances by address
CREATE TABLE IF NOT EXISTS token_balances (
    token_id VARCHAR(64) NOT NULL,
    address VARCHAR(64) NOT NULL,
    balance NUMERIC NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (token_id, address)
);

-- Table to store token information
CREATE TABLE IF NOT EXISTS tokens (
    token_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    decimals INTEGER DEFAULT 0,
    total_supply NUMERIC,
    first_seen_height INTEGER,
    first_seen_timestamp TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indices for better query performance
CREATE INDEX IF NOT EXISTS idx_token_balances_token_id ON token_balances(token_id);
CREATE INDEX IF NOT EXISTS idx_token_balances_address ON token_balances(address);
CREATE INDEX IF NOT EXISTS idx_token_balances_balance ON token_balances(balance DESC);

-- Function to update token balances when processing new blocks/transactions
CREATE OR REPLACE FUNCTION update_token_balances()
RETURNS TRIGGER AS $$
DECLARE
    v_address VARCHAR;
    v_token_id VARCHAR;
    v_amount NUMERIC;
BEGIN
    -- For each asset in a new output, update token balances
    IF (TG_OP = 'INSERT') THEN
        -- Get the address from the outputs table
        SELECT o.address INTO v_address
        FROM outputs o
        WHERE o.box_id = NEW.box_id;
        
        -- Exit early if address is null
        IF v_address IS NULL THEN
            RETURN NEW;
        END IF;
        
        v_token_id := NEW.token_id;
        v_amount := NEW.amount;
        
        -- Skip invalid records
        IF v_token_id IS NULL OR v_amount IS NULL THEN
            RETURN NEW;
        END IF;
        
        -- Update token balances
        INSERT INTO token_balances (token_id, address, balance)
        VALUES (v_token_id, v_address, v_amount)
        ON CONFLICT (token_id, address) DO UPDATE
        SET balance = token_balances.balance + v_amount,
            last_updated = NOW();
        
        -- Ensure token exists in tokens table
        INSERT INTO tokens (token_id, first_seen_height, first_seen_timestamp)
        VALUES (
            v_token_id, 
            (SELECT creation_height FROM outputs WHERE box_id = NEW.box_id), 
            NOW()
        )
        ON CONFLICT (token_id) DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to update token balances
DROP TRIGGER IF EXISTS update_token_balances_on_asset ON assets;
CREATE TRIGGER update_token_balances_on_asset
AFTER INSERT ON assets
FOR EACH ROW
EXECUTE FUNCTION update_token_balances();

-- Function to update token information from outputs table
CREATE OR REPLACE FUNCTION update_token_info()
RETURNS TRIGGER AS $$
DECLARE
    v_token_id VARCHAR;
    v_name VARCHAR;
    v_description TEXT;
    v_decimals INTEGER;
    v_register_r4 JSON;
    v_register_r5 JSON;
    v_register_r6 JSON;
BEGIN
    -- Process only if we have additional registers
    IF NEW.additional_registers IS NULL THEN
        RETURN NEW;
    END IF;
    
    -- Extract values from registers if present
    v_register_r4 := NEW.additional_registers->'R4';
    v_register_r5 := NEW.additional_registers->'R5';
    v_register_r6 := NEW.additional_registers->'R6';
    
    -- Get the token ID from the assets table
    SELECT a.token_id INTO v_token_id
    FROM assets a
    WHERE a.box_id = NEW.box_id
    LIMIT 1;
    
    -- Skip if token_id is null
    IF v_token_id IS NULL THEN
        RETURN NEW;
    END IF;
    
    -- Try to extract token name from R4
    IF v_register_r4 IS NOT NULL AND v_register_r4->>'renderedValue' IS NOT NULL THEN
        v_name := v_register_r4->>'renderedValue';
    END IF;
    
    -- Try to extract token description from R5
    IF v_register_r5 IS NOT NULL AND v_register_r5->>'renderedValue' IS NOT NULL THEN
        v_description := v_register_r5->>'renderedValue';
    END IF;
    
    -- Try to extract decimals from R6
    IF v_register_r6 IS NOT NULL AND v_register_r6->>'renderedValue' IS NOT NULL THEN
        BEGIN
            v_decimals := (v_register_r6->>'renderedValue')::INTEGER;
        EXCEPTION WHEN OTHERS THEN
            v_decimals := 0;
        END;
    END IF;
    
    -- Update token information
    UPDATE tokens
    SET 
        name = COALESCE(v_name, name),
        description = COALESCE(v_description, description),
        decimals = COALESCE(v_decimals, decimals),
        last_updated = NOW()
    WHERE token_id = v_token_id;
    
    -- Calculate total supply
    UPDATE tokens t
    SET total_supply = (
        SELECT SUM(tb.balance)
        FROM token_balances tb
        WHERE tb.token_id = t.token_id
    )
    WHERE token_id = v_token_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update token information
DROP TRIGGER IF EXISTS update_token_info_trigger ON outputs;
CREATE TRIGGER update_token_info_trigger
AFTER INSERT ON outputs
FOR EACH ROW
EXECUTE FUNCTION update_token_info();

-- Function to get token holders with pagination
CREATE OR REPLACE FUNCTION get_token_holders(
    p_token_id VARCHAR,
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS JSONB AS $$
DECLARE
    v_holders JSONB;
    v_token JSONB;
    v_total_holders INTEGER;
    v_total_supply NUMERIC;
BEGIN
    -- Get token information
    SELECT 
        jsonb_build_object(
            'tokenId', t.token_id,
            'name', t.name,
            'description', t.description,
            'decimals', t.decimals,
            'totalSupply', t.total_supply
        )
    INTO v_token
    FROM tokens t
    WHERE t.token_id = p_token_id;
    
    -- Return error if token not found
    IF v_token IS NULL THEN
        RETURN jsonb_build_object(
            'error', 'Token not found',
            'status', 404
        );
    END IF;
    
    -- Get total holders count
    SELECT COUNT(*), SUM(balance)
    INTO v_total_holders, v_total_supply
    FROM token_balances
    WHERE token_id = p_token_id;
    
    -- Get paginated holders
    SELECT jsonb_agg(
        jsonb_build_object(
            'address', address,
            'balance', balance,
            'percentage', ROUND((balance / NULLIF(v_total_supply, 0) * 100)::NUMERIC, 2)
        )
    )
    INTO v_holders
    FROM (
        SELECT address, balance
        FROM token_balances
        WHERE token_id = p_token_id
        ORDER BY balance DESC
        LIMIT p_limit
        OFFSET p_offset
    ) h;
    
    -- Return response
    RETURN jsonb_build_object(
        'token', v_token,
        'holders', COALESCE(v_holders, '[]'::JSONB),
        'total', v_total_holders,
        'limit', p_limit,
        'offset', p_offset
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get top tokens by holder count
CREATE OR REPLACE FUNCTION get_top_tokens(
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS JSONB AS $$
DECLARE
    v_tokens JSONB;
    v_total INTEGER;
BEGIN
    -- Get total tokens count
    SELECT COUNT(DISTINCT token_id)
    INTO v_total
    FROM token_balances;
    
    -- Get paginated tokens
    SELECT jsonb_agg(
        jsonb_build_object(
            'tokenId', t.token_id,
            'name', t.name,
            'description', t.description,
            'decimals', t.decimals,
            'totalSupply', t.total_supply,
            'holderCount', h.holder_count
        )
    )
    INTO v_tokens
    FROM (
        SELECT token_id, COUNT(*) as holder_count
        FROM token_balances
        GROUP BY token_id
        ORDER BY COUNT(*) DESC
        LIMIT p_limit
        OFFSET p_offset
    ) h
    JOIN tokens t ON t.token_id = h.token_id;
    
    -- Return response
    RETURN jsonb_build_object(
        'tokens', COALESCE(v_tokens, '[]'::JSONB),
        'total', v_total,
        'limit', p_limit,
        'offset', p_offset
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get address tokens
CREATE OR REPLACE FUNCTION get_address_tokens(
    p_address VARCHAR,
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS JSONB AS $$
DECLARE
    v_tokens JSONB;
    v_total INTEGER;
BEGIN
    -- Get total tokens count for address
    SELECT COUNT(*)
    INTO v_total
    FROM token_balances
    WHERE address = p_address;
    
    -- Get paginated tokens
    SELECT jsonb_agg(
        jsonb_build_object(
            'tokenId', t.token_id,
            'name', t.name,
            'description', t.description,
            'decimals', t.decimals,
            'balance', tb.balance
        )
    )
    INTO v_tokens
    FROM (
        SELECT token_id, balance
        FROM token_balances
        WHERE address = p_address
        ORDER BY balance DESC
        LIMIT p_limit
        OFFSET p_offset
    ) tb
    JOIN tokens t ON t.token_id = tb.token_id;
    
    -- Return response
    RETURN jsonb_build_object(
        'address', p_address,
        'tokens', COALESCE(v_tokens, '[]'::JSONB),
        'total', v_total,
        'limit', p_limit,
        'offset', p_offset
    );
END;
$$ LANGUAGE plpgsql; 