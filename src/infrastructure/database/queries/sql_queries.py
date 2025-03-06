create_table_queries = {
    "create_am_pm_bots_table": """
    CREATE TABLE am_pm_bots (
        id SERIAL PRIMARY KEY,
        account_am VARCHAR(12) REFERENCES wcw_accounts(wallet),
        account_pm VARCHAR(12) REFERENCES wcw_accounts(wallet),
        tool_nft_id VARCHAR(13) REFERENCES mining_tools(nft_id)
);
    """,
    "create_single_bots_table": """
    CREATE TABLE single_bots (
        id SERIAL PRIMARY KEY,
        account VARCHAR(12) REFERENCES wcw_accounts(wallet),
        tool_nft_id VARCHAR(13) REFERENCES mining_tools(nft_id),
        start_time SMALLINT NOT NULL DEFAULT 0,
        end_time SMALLINT NOT NULL DEFAULT 12
);
    """,
    "add_tools_table_query": """
    CREATE TABLE mining_tools (
        nft_id VARCHAR(13) PRIMARY KEY,
        tool_type VARCHAR(30) NOT NULL,
        owner VARCHAR(12) NOT NULL, FOREIGN KEY (owner) REFERENCES wcw_accounts(wallet)
    );
    """,
    "add_accounts_table_query": """
    CREATE TABLE wcw_accounts (
        wallet VARCHAR(12) PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        token VARCHAR(40) NOT NULL,
        key VARCHAR(51),
        CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
        CONSTRAINT token_format CHECK (CHAR_LENGTH(token) = 40)
    );
    """,
    "add_aw_state_table": """
    CREATE TABLE aw_miners (
        aw_id         serial                NOT NULL,
        wallet        varchar(12)           NOT NULL,
        is_registered boolean DEFAULT false NOT NULL,
        is_flagged    boolean DEFAULT false NOT NULL,
        is_archived   boolean DEFAULT false NOT NULL,
        points        integer DEFAULT 0,
        fed_tlm       NUMERIC(10, 4),
    
        PRIMARY KEY ( aw_id ),
        FOREIGN KEY ( wallet )
            REFERENCES wcw_accounts (wallet)
    
    );
    """,
    "add_transactions_table_query": """ 
    CREATE TABLE transactions (
        id CHAR(64) PRIMARY KEY,
        mine_time timestamp,
        block_time timestamp without time zone,
        wallet VARCHAR(12) REFERENCES wcw_accounts(wallet),
        bag_item CHAR(13) REFERENCES mining_tools(nft_id),
        bounty VARCHAR(10),
        land_id CHAR(13)
        
    );
""",
    # другие запросы...
}

alter_table_queries = {
    "add_2_nft_field_to_bots": """
    ALTER TABLE bots
    ADD COLUMN tool_nft_id_2 VARCHAR(13) REFERENCES mining_tools(nft_id) DEFAULT NULL,
    ADD COLUMN tool_nft_id_3 VARCHAR(13) REFERENCES mining_tools(nft_id) DEFAULT NULL;
    """
}

select_queries = {
    "get_wcw_accounts_by_wallet": """
        SELECT * 
        FROM wcw_accounts 
        WHERE wallet IN ( %s );
        """,
    "get_random_wallet_with_key": """
        SELECT * 
        FROM wcw_accounts 
        WHERE wcw_accounts.key is not null 
        ORDER BY RANDOM() 
        LIMIT 1;
        """,
    "get_bots": """
    SELECT 
        am.wallet AS account_am_wallet,
        am.email AS account_am_email,
        am.token AS account_am_token,
        am.key AS account_am_key,
        pm.wallet AS account_pm_wallet,
        pm.email AS account_pm_email,
        pm.token AS account_pm_token,
        pm.key AS account_pm_key,
        tool1.nft_id AS tool1_nft_id,
        tool1.tool_type AS tool1_tool_type,
        tool2.nft_id AS tool2_nft_id,
        tool2.tool_type AS tool2_tool_type,
        tool3.nft_id AS tool3_nft_id,
        tool3.tool_type AS tool3_tool_type
    FROM
        bots
    INNER JOIN
        wcw_accounts AS am ON bots.account_am = am.wallet
    INNER JOIN
        wcw_accounts AS pm ON bots.account_pm = pm.wallet
    INNER JOIN
        mining_tools AS tool1 ON bots.tool_nft_id = tool1.nft_id
    LEFT JOIN
        mining_tools AS tool2 ON bots.tool_nft_id_2 = tool2.nft_id
    LEFT JOIN
        mining_tools AS tool3 ON bots.tool_nft_id_3 = tool3.nft_id;
    """,
    "get_tool_by_id": """
    SELECT 
        nft_id, tool_type
    from alienworlds.public.mining_tools
    where nft_id in ( %s );
    """,
    "get_single_bots": """
    SELECT 
        wallet, email, token, key, 
        tool1.nft_id as tool1_nft_id, tool1.tool_type as tool1_tool_type, 
        tool2.nft_id as tool2_nft_id, tool2.tool_type as tool2_tool_type, 
        tool3.nft_id as tool3_nft_id, tool3.tool_type as tool3_tool_type, 
        start_time, end_time
    FROM
        single_bots
    INNER JOIN
        wcw_accounts ON single_bots.account = wcw_accounts.wallet
    INNER JOIN
        mining_tools AS tool1 ON single_bots.tool_nft_id = tool1.nft_id
   LEFT JOIN
        mining_tools AS tool2 ON single_bots.tool_nft_id2 = tool2.nft_id
    LEFT JOIN
        mining_tools AS tool3 ON single_bots.tool_nft_id3 = tool3.nft_id;
    """,
    "get_flag_bots": """
     SELECT 
         account,
         tool1.nft_id as tool1_nft_id, tool1.tool_type as tool1_tool_type, 
         tool2.nft_id as tool2_nft_id, tool2.tool_type as tool2_tool_type, 
         tool3.nft_id as tool3_nft_id, tool3.tool_type as tool3_tool_type 
     FROM
         flag_bots
     INNER JOIN
         mining_tools AS tool1 ON flag_bots.tool_nft_id = tool1.nft_id
     LEFT JOIN
         mining_tools AS tool2 ON flag_bots.tool_nft_id2 = tool2.nft_id
     LEFT JOIN
         mining_tools AS tool3 ON flag_bots.tool_nft_id3 = tool3.nft_id
     WHERE enabled = true;

    ;
 """,
    "get_two_wallets": """
    SELECT wallet 
    FROM wcw_accounts 
    WHERE wallet NOT IN (
        SELECT account_am FROM bots
        UNION
        SELECT account_pm FROM bots
    )
    LIMIT 4;
    """,
    "get_all_bots_wallets": """
    SELECT account_am AS wallet FROM bots
    UNION
    SELECT account_pm AS wallet FROM bots;
    """,
    "get_wcw_accounts_in_bots": """
    SELECT * 
    FROM wcw_accounts 
    WHERE wallet IN (
        SELECT account_am FROM bots
        UNION
        SELECT account_pm FROM bots
    );""",
    "get_wcw_accounts_not_in_bots": """
    SELECT wallet 
    FROM wcw_accounts 
    WHERE wallet NOT IN (
        SELECT account_am FROM bots
        UNION
        SELECT account_pm FROM bots
    );""",
    "get_wcw_accounts_not_in_bots_not_flagged": """
    SELECT wallet 
    FROM wcw_accounts 
    WHERE wallet NOT IN (
        SELECT account_am FROM bots
        UNION
        SELECT account_pm FROM bots
    )
    AND wallet NOT IN (
    SELECT wallet FROM aw_miners WHERE is_flagged = TRUE
    );""",
    "get_all_aw_miners": """
    SELECT wallet FROM aw_miners
    ;""",
    "get_all_flagged_aw_miners": """
    SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, aw_miners.is_flagged
    FROM wcw_accounts
    INNER JOIN aw_miners ON wcw_accounts.wallet = aw_miners.wallet
    WHERE is_flagged = true AND wcw_accounts.wallet != 'eefoo.c.wam' AND aw_miners.fed_tlm > 10
    AND wcw_accounts.key is not null
    ORDER BY aw_miners.points DESC 
    ;""",
    "get_all_flagged_single_bot": """
    SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, aw_miners.is_flagged
    FROM wcw_accounts
    INNER JOIN aw_miners ON wcw_accounts.wallet = aw_miners.wallet
    --- INNER JOIN single_bots ON wcw_accounts.wallet = single_bots.account
    WHERE is_flagged = true
    --- AND wcw_accounts.wallet LIKE '%%.wam'
    AND wcw_accounts.wallet != 'eefoo.c.wam'
    AND wcw_accounts.key is not null
    ---- AND wcw_accounts.wallet NOT IN (SELECT account FROM single_bots)
    ORDER BY aw_miners.points DESC
    LIMIT 1;
    """,
    "get_all_not_flagged_single_bot": """
    SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, aw_miners.is_flagged
    FROM wcw_accounts

    INNER JOIN aw_miners ON wcw_accounts.wallet = aw_miners.wallet
    --- INNER JOIN single_bots ON wcw_accounts.wallet = single_bots.account
    INNER JOIN single_bot_view ON wcw_accounts.wallet = single_bot_view.account
    -- where tool_type in ('Barrel Digger', 'Large Capacitor')
    --- WHERE is_flagged = false 

    ORDER BY aw_miners.points DESC;""",
    "get_flag_record": """
    SELECT is_flagged
    FROM aw_miners
    WHERE wallet = %s
    ;""",
    "get_upgraded_miners_list": """
    SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, aw_miners.points
    FROM wcw_accounts
    LEFT JOIN aw_miners ON wcw_accounts.wallet = aw_miners.wallet
    WHERE aw_miners.points > 2840 and aw_miners.is_flagged = false and aw_miners.is_registered = true
    and wcw_accounts.key is not null and wcw_accounts.wallet not like '%%.wam'
    and wcw_accounts.wallet not in (SELECT account FROM single_bots);
    """,
    "get_free_common_tools": """
        SELECT nft_id, tool_type
        FROM mining_tools
        WHERE nft_id NOT IN
        (
            SELECT DISTINCT tool_nft_id FROM single_bots WHERE tool_nft_id IS NOT NULL
            UNION
            SELECT DISTINCT tool_nft_id2 FROM single_bots WHERE tool_nft_id2 IS NOT NULL
            UNION
            SELECT DISTINCT tool_nft_id3 FROM single_bots WHERE tool_nft_id3 IS NOT NULL
        )  AND (tool_type = 'Shiny Explosive' OR tool_type = 'Certified Kol Digger')
    """,
    "get_tool_id_list_by_type": """SELECT nft_id from mining_tools WHERE tool_type = 'Certified Kol Digger';""",
    "get_unused_wam": """
        SELECT wallet from alienworlds.public.wcw_accounts
        where wallet ~ '.wam$' and wallet in (SELECT wallet from alienworlds.public.aw_miners
         where aw_miners.is_flagged = false and  points is null)
    """,
    "get_new_12_sym": """
    SELECT wallet from alienworlds.public.wcw_accounts
    where wallet !~ '.wam$' and wallet not in (SELECT wallet from alienworlds.public.aw_miners)
    and wallet not in ('owiroobazafa', 'muraramapeqi', 'aforutswakhg', 'masterflomas')
    """,
    "get_not_banned_12_sym": """
    SELECT wallet, email, token, key, true from alienworlds.public.wcw_accounts
    where wallet ~ '.wam$' 
    and key is not null
    and wallet not in (SELECT wallet from alienworlds.public.aw_miners where aw_miners.is_flagged = false)
    ---and wallet not in ('owiroobazafa', 'muraramapeqi', 'aforutswakhg', 'masterflomas')
    and wallet not in (SELECT account from alienworlds.public.single_bots)
    """,
    "get_all_unused_tool_by_type": """
    SELECT nft_id
    FROM alienworlds.public.mining_tools
    WHERE tool_type = 'Certified Kol Digger'
    AND nft_id NOT IN (
    SELECT tool_nft_id
    FROM alienworlds.public.single_bots
    WHERE alienworlds.public.single_bots.account IN (
        SELECT wallet
        FROM alienworlds.public.aw_miners
        WHERE is_flagged = false
        )
    UNION
    SELECT tool_nft_id2
    FROM alienworlds.public.single_bots
    WHERE tool_nft_id2 IS NOT NULL
    AND alienworlds.public.single_bots.account IN (
        SELECT wallet
        FROM alienworlds.public.aw_miners
        WHERE is_flagged = false
        )
    UNION
    SELECT tool_nft_id3
    FROM alienworlds.public.single_bots
    WHERE tool_nft_id3 IS NOT NULL
    AND alienworlds.public.single_bots.account IN (
        SELECT wallet
        FROM alienworlds.public.aw_miners
        WHERE is_flagged = false
        )
    )""",
    "get_ready_to_use_upgraded_account": """
        SELECT wallet from alienworlds.public.aw_miners 
        where aw_miners.wallet not like '%.wam' and wallet NOT IN (SELECT account from alienworlds.public.single_bots) and is_flagged = false
    """,
    "get_ready_to_use_upgraded_account_flagcheck": """
      SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, false
      FROM wcw_accounts 
      where wallet in (
      SELECT wallet from alienworlds.public.aw_miners 
      WHERE is_flagged = false 
          and points between 2840 and 6840
          and wallet not like '%%.wam'
          and wallet not in (SELECT single_bots.account from single_bots))
      limit 760;
  """,
    "get_for_repeat_use": """
        SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, false
      FROM wcw_accounts 
      where wallet in (select aw_miners.wallet from public.aw_miners
        where wallet not like '%%.wam'
          and wallet not in (select account from single_bots)
          and is_flagged = false and points between 0 and 300000);
  """,
    "query_flagged_miners_with_zero_points": """
    SELECT wcw_accounts.wallet, wcw_accounts.email, wcw_accounts.token, wcw_accounts.key, false
      FROM wcw_accounts 
      where wallet in (select wallet from public.aw_miners
        where wallet not like '%%.wam'
        and wallet not in (select account from single_bots)
        and is_flagged = false and points = 0);
    """,
}
