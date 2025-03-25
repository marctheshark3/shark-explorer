-- Fix for transaction API endpoint issues
-- Adds better error handling and fixes potential issues with NULL values

-- Function to get a transaction by ID with error handling
CREATE OR REPLACE FUNCTION get_transaction_by_id(p_tx_id VARCHAR)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_inputs JSONB;
    v_outputs JSONB;
    v_error TEXT;
    v_exists BOOLEAN;
BEGIN
    -- Check if transaction exists
    SELECT EXISTS(SELECT 1 FROM transactions WHERE id = p_tx_id) INTO v_exists;
    
    IF NOT v_exists THEN
        RETURN jsonb_build_object(
            'error', 'Transaction not found',
            'status', 404
        );
    END IF;
    
    -- Try to get transaction details with NULL handling
    BEGIN
        SELECT 
            jsonb_build_object(
                'id', t.id,
                'headerId', COALESCE(t.header_id, ''),
                'inclusionHeight', COALESCE(t.inclusion_height, 0),
                'timestamp', COALESCE(extract(epoch from t.timestamp) * 1000, 0),
                'index', COALESCE(t.index, 0),
                'confirmationsCount', COALESCE((SELECT MAX(height) FROM blocks) - t.inclusion_height + 1, 0),
                'size', COALESCE(t.size, 0)
            )
        INTO v_result
        FROM transactions t
        WHERE t.id = p_tx_id;
        
        -- Get inputs (with error handling)
        BEGIN
            SELECT 
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'id', COALESCE(i.box_id, ''),
                            'address', COALESCE(i.address, ''),
                            'value', COALESCE(i.value, 0),
                            'index', COALESCE(i.index, 0),
                            'spendingProof', COALESCE(
                                jsonb_build_object(
                                    'proofBytes', COALESCE(i.proof_bytes, ''),
                                    'extension', COALESCE(i.extension, '{}'::JSONB)
                                ),
                                '{}'::JSONB
                            ),
                            'transactionId', COALESCE(i.tx_id, '')
                        )
                    ),
                    '[]'::JSONB
                ) 
            INTO v_inputs
            FROM inputs i
            WHERE i.tx_id = p_tx_id
            ORDER BY i.index;
            
            v_result = v_result || jsonb_build_object('inputs', v_inputs);
        EXCEPTION WHEN OTHERS THEN
            v_error = SQLERRM;
            v_result = v_result || jsonb_build_object('inputs', '[]'::JSONB);
            v_result = v_result || jsonb_build_object('inputsError', v_error);
        END;
        
        -- Get outputs (with error handling)
        BEGIN
            SELECT 
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'id', COALESCE(o.box_id, ''),
                            'txId', COALESCE(o.tx_id, ''),
                            'value', COALESCE(o.value, 0),
                            'index', COALESCE(o.index, 0),
                            'creationHeight', COALESCE(o.creation_height, 0),
                            'ergoTree', COALESCE(o.ergo_tree, ''),
                            'address', COALESCE(o.address, ''),
                            'assets', COALESCE(o.assets, '[]'::JSONB),
                            'additionalRegisters', COALESCE(o.additional_registers, '{}'::JSONB)
                        )
                    ),
                    '[]'::JSONB
                )
            INTO v_outputs
            FROM outputs o
            WHERE o.tx_id = p_tx_id
            ORDER BY o.index;
            
            v_result = v_result || jsonb_build_object('outputs', v_outputs);
        EXCEPTION WHEN OTHERS THEN
            v_error = SQLERRM;
            v_result = v_result || jsonb_build_object('outputs', '[]'::JSONB);
            v_result = v_result || jsonb_build_object('outputsError', v_error);
        END;
        
        RETURN v_result;
    EXCEPTION WHEN OTHERS THEN
        v_error = SQLERRM;
        RETURN jsonb_build_object(
            'error', v_error,
            'status', 500,
            'txId', p_tx_id
        );
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to get transaction inputs by transaction ID with error handling
CREATE OR REPLACE FUNCTION get_transaction_inputs(p_tx_id VARCHAR)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_error TEXT;
    v_exists BOOLEAN;
BEGIN
    -- Check if transaction exists
    SELECT EXISTS(SELECT 1 FROM transactions WHERE id = p_tx_id) INTO v_exists;
    
    IF NOT v_exists THEN
        RETURN jsonb_build_object(
            'error', 'Transaction not found',
            'status', 404
        );
    END IF;
    
    -- Try to get inputs with proper error handling
    BEGIN
        SELECT 
            COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'id', COALESCE(i.box_id, ''),
                        'address', COALESCE(i.address, ''),
                        'value', COALESCE(i.value, 0),
                        'index', COALESCE(i.index, 0),
                        'spendingProof', COALESCE(
                            jsonb_build_object(
                                'proofBytes', COALESCE(i.proof_bytes, ''),
                                'extension', COALESCE(i.extension, '{}'::JSONB)
                            ),
                            '{}'::JSONB
                        ),
                        'transactionId', COALESCE(i.tx_id, '')
                    )
                ),
                '[]'::JSONB
            ) 
        INTO v_result
        FROM inputs i
        WHERE i.tx_id = p_tx_id
        ORDER BY i.index;
        
        RETURN v_result;
    EXCEPTION WHEN OTHERS THEN
        v_error = SQLERRM;
        RETURN jsonb_build_object(
            'error', v_error,
            'status', 500,
            'txId', p_tx_id
        );
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to get transaction outputs by transaction ID with error handling
CREATE OR REPLACE FUNCTION get_transaction_outputs(p_tx_id VARCHAR)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_error TEXT;
    v_exists BOOLEAN;
BEGIN
    -- Check if transaction exists
    SELECT EXISTS(SELECT 1 FROM transactions WHERE id = p_tx_id) INTO v_exists;
    
    IF NOT v_exists THEN
        RETURN jsonb_build_object(
            'error', 'Transaction not found',
            'status', 404
        );
    END IF;
    
    -- Try to get outputs with proper error handling
    BEGIN
        SELECT 
            COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'id', COALESCE(o.box_id, ''),
                        'txId', COALESCE(o.tx_id, ''),
                        'value', COALESCE(o.value, 0),
                        'index', COALESCE(o.index, 0),
                        'creationHeight', COALESCE(o.creation_height, 0),
                        'ergoTree', COALESCE(o.ergo_tree, ''),
                        'address', COALESCE(o.address, ''),
                        'assets', COALESCE(o.assets, '[]'::JSONB),
                        'additionalRegisters', COALESCE(o.additional_registers, '{}'::JSONB)
                    )
                ),
                '[]'::JSONB
            )
        INTO v_result
        FROM outputs o
        WHERE o.tx_id = p_tx_id
        ORDER BY o.index;
        
        RETURN v_result;
    EXCEPTION WHEN OTHERS THEN
        v_error = SQLERRM;
        RETURN jsonb_build_object(
            'error', v_error,
            'status', 500,
            'txId', p_tx_id
        );
    END;
END;
$$ LANGUAGE plpgsql;

-- Create an index on transactions.id if it doesn't exist already
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'transactions' AND indexname = 'idx_transactions_id'
    ) THEN
        CREATE INDEX idx_transactions_id ON transactions(id);
    END IF;
END$$;

-- Create indices on inputs and outputs tables for better performance
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'inputs' AND indexname = 'idx_inputs_tx_id'
    ) THEN
        CREATE INDEX idx_inputs_tx_id ON inputs(tx_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'outputs' AND indexname = 'idx_outputs_tx_id'
    ) THEN
        CREATE INDEX idx_outputs_tx_id ON outputs(tx_id);
    END IF;
END$$; 