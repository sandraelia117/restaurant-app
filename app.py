import streamlit as st
from db_manager import get_data, execute_procedure, insert_pizza_sale
from datetime import datetime, date

st.set_page_config(page_title="Pizza RMS - Admin", layout="wide", page_icon="🍕")
st.title("🍕 hyper transactuion system")

# ── تهيئة session_state لحفظ آخر تأثير من Add Pizza Sale ──
if 'last_order_impact' not in st.session_state:
    st.session_state['last_order_impact'] = None
# الشكل: {
#   'pizza_name': str, 'quantity': int, 'size': str, 'timestamp': str,
#   'changed_ing':  DataFrame (INGREDIENT قبل/بعد),
#   'changed_ps':   DataFrame (INVENTORY_FROM_PIZZA_SALES قبل/بعد),
#   'changed_ref':  DataFrame (INVENTORY_REFINED قبل/بعد),
# }

menu = ["Data Management",  "Add Pizza Sale", "Inventory Monitor"]
choice = st.sidebar.selectbox("Select Mode", menu)

# ── بادج في السايدبار لو في طلب محفوظ ──
if st.session_state['last_order_impact']:
    impact = st.session_state['last_order_impact']
    st.sidebar.info(
        f"🕐 آخر طلب محفوظ:\n\n"
        f"**{impact['pizza_name']}** × {impact['quantity']} ({impact['size']})\n\n"
        f"الساعة {impact['timestamp']}"
    )
    if st.sidebar.button("🗑️ مسح آخر طلب"):
        st.session_state['last_order_impact'] = None
        st.rerun()

table_map = {
    "Customers": "CUSTOMERS",
    "Employees": "EMPLOYEES",
    "Ingredients": "INGREDIENT",
    "Suppliers": "SUPPLIERS",
    "Tables": "TABLES_RMS",
    "Menu Items": "MENU_ITEM_REFINED",
    "Orders": "ORDERS_REFINED",
    "Inventory": "INVENTORY_REFINED",
    "Inventory Sales": "INVENTORY_FROM_PIZZA_SALES",
    "Reservations": "RESERVATIONS",
    "Pizza Sales": "PIZZA_SALES"
}

# ════════════════════════════════════════════
#  DATA MANAGEMENT
# ════════════════════════════════════════════
if choice == "Data Management":
    st.subheader("View Database Tables")
    selected_table = st.selectbox("Select Table:", list(table_map.keys()))
    try:
        df = get_data(f"SELECT * FROM {table_map[selected_table]}")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load: {e}")



# ════════════════════════════════════════════
#  ADD PIZZA SALE
# ════════════════════════════════════════════
elif choice == "Add Pizza Sale":
    st.subheader("Add Pizza to Order")
    st.info("The Trigger will reduce INGREDIENT table automatically after adding!")

    try:
        orders_df = get_data("SELECT order_id FROM ORDERS_REFINED ORDER BY order_id DESC")
        menu_df   = get_data("SELECT menu_item_id, p_name, p_size, unit_price, ingredients_list FROM MENU_ITEM_REFINED")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        order_id_sel = st.selectbox(
            "Select Order:",
            orders_df['ORDER_ID'].tolist() if not orders_df.empty else []
        )
        quantity = st.number_input("Quantity", min_value=1, max_value=50, value=1)

    with col2:
        available_sizes = sorted(menu_df['P_SIZE'].dropna().unique().tolist()) if not menu_df.empty else []
        size_labels  = {'L': 'Large (L)', 'M': 'Medium (M)', 'S': 'Small (S)'}
        size_display = [size_labels.get(s, s) for s in available_sizes]
        size_map     = {size_labels.get(s, s): s for s in available_sizes}

        selected_size_display = st.selectbox("Pizza Size:", size_display if size_display else ["No sizes available"])
        selected_size = size_map.get(selected_size_display, None)

        filtered_menu = menu_df[menu_df['P_SIZE'] == selected_size] if selected_size and not menu_df.empty else menu_df
        menu_options  = filtered_menu['P_NAME'].tolist() if not filtered_menu.empty else []
        selected_pizza_name = st.selectbox("Select Pizza:", menu_options)

    if selected_pizza_name and not filtered_menu.empty:
        pizza_row = filtered_menu[filtered_menu['P_NAME'] == selected_pizza_name].iloc[0]
        st.write("---")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Unit Price", f"${pizza_row['UNIT_PRICE']:.2f}")
        col_b.metric("Size", pizza_row['P_SIZE'])
        col_c.metric("Total", f"${pizza_row['UNIT_PRICE'] * quantity:.2f}")
        st.caption(f"Ingredients: {pizza_row['INGREDIENTS_LIST']}")

    if st.button("Confirm Order and Reduce Inventory", type="primary"):
        if selected_pizza_name and not filtered_menu.empty:
            pizza_row = filtered_menu[filtered_menu['P_NAME'] == selected_pizza_name].iloc[0]

            try:
                max_id_df  = get_data("SELECT NVL(MAX(pizza_id), 0) + 1 AS new_id FROM PIZZA_SALES")
                new_pizza_id = int(max_id_df.iloc[0]['NEW_ID'])
            except Exception:
                new_pizza_id = 1

            pizza_data = {
                'pizza_id':          new_pizza_id,
                'order_id':          int(order_id_sel),
                'pizza_name_id':     str(pizza_row['MENU_ITEM_ID']),
                'quantity':          int(quantity),
                'order_date':        date.today(),
                'order_time':        datetime.now().strftime('%H:%M:%S'),
                'unit_price':        float(pizza_row['UNIT_PRICE']),
                'total_price':       float(pizza_row['UNIT_PRICE']) * int(quantity),
                'pizza_size':        str(pizza_row['P_SIZE']),
                'pizza_category':    'Pizza',
                'pizza_ingredients': str(pizza_row['INGREDIENTS_LIST']),
                'pizza_name':        str(pizza_row['P_NAME']),
            }

            # ── قبل ──
            ing_before = get_data("""
                SELECT i.ingredient_id, i.ingredient_name, ir.stock_qty AS stock_qty
                FROM INVENTORY_REFINED ir
                JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
            """)
            inv_ps_before  = get_data("SELECT ingredient_name, current_stock_qty FROM INVENTORY_FROM_PIZZA_SALES")
            inv_ref_before = get_data("""
                SELECT i.ingredient_name, ir.stock_qty
                FROM INVENTORY_REFINED ir
                JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
            """)

            try:
                insert_pizza_sale(pizza_data)
                get_data.clear()

                # ── بعد ──
                ing_after = get_data("""
                    SELECT i.ingredient_id, i.ingredient_name, ir.stock_qty AS stock_qty
                    FROM INVENTORY_REFINED ir
                    JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
                """)
                inv_ps_after  = get_data("SELECT ingredient_name, current_stock_qty FROM INVENTORY_FROM_PIZZA_SALES")
                inv_ref_after = get_data("""
                    SELECT i.ingredient_name, ir.stock_qty
                    FROM INVENTORY_REFINED ir
                    JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
                """)

                st.success(f"✅ Added {quantity}x {selected_pizza_name} successfully!")

                pizza_ingredients_str = str(pizza_row['INGREDIENTS_LIST'])

                # ── INGREDIENT diff ──
                merged_ing = ing_before.merge(ing_after, on=['INGREDIENT_ID', 'INGREDIENT_NAME'], suffixes=('_BEFORE', '_AFTER'))
                merged_ing = merged_ing[merged_ing['INGREDIENT_NAME'].apply(lambda n: n in pizza_ingredients_str)].copy()
                changed_ing = merged_ing[merged_ing['STOCK_QTY_BEFORE'] != merged_ing['STOCK_QTY_AFTER']].copy()
                changed_ing['REDUCED BY'] = changed_ing['STOCK_QTY_BEFORE'] - changed_ing['STOCK_QTY_AFTER']

                # ── INVENTORY_FROM_PIZZA_SALES diff ──
                merged_ps  = inv_ps_before.merge(inv_ps_after, on='INGREDIENT_NAME', suffixes=('_BEFORE', '_AFTER'))
                changed_ps = merged_ps[merged_ps['CURRENT_STOCK_QTY_BEFORE'] != merged_ps['CURRENT_STOCK_QTY_AFTER']].copy()
                changed_ps['REDUCED BY'] = changed_ps['CURRENT_STOCK_QTY_BEFORE'] - changed_ps['CURRENT_STOCK_QTY_AFTER']

                # ── INVENTORY_REFINED diff ──
                merged_ref  = inv_ref_before.merge(inv_ref_after, on='INGREDIENT_NAME', suffixes=('_BEFORE', '_AFTER'))
                changed_ref = merged_ref[merged_ref['STOCK_QTY_BEFORE'] != merged_ref['STOCK_QTY_AFTER']].copy()
                changed_ref['REDUCED BY'] = changed_ref['STOCK_QTY_BEFORE'] - changed_ref['STOCK_QTY_AFTER']

                # ══ حفظ كل ده في session_state ══
                st.session_state['last_order_impact'] = {
                    'pizza_name':  str(pizza_row['P_NAME']),
                    'quantity':    int(quantity),
                    'size':        str(pizza_row['P_SIZE']),
                    'timestamp':   datetime.now().strftime('%H:%M:%S'),
                    'changed_ing': changed_ing.copy(),
                    'changed_ps':  changed_ps.copy(),
                    'changed_ref': changed_ref.copy(),
                }

                # ── عرض INGREDIENT diff ──
                st.write("### 📉 تأثير على INGREDIENT")
                if not changed_ing.empty:
                    st.dataframe(
                        changed_ing[['INGREDIENT_NAME', 'STOCK_QTY_BEFORE', 'STOCK_QTY_AFTER', 'REDUCED BY']].rename(columns={
                            'INGREDIENT_NAME':  'المكوّن',
                            'STOCK_QTY_BEFORE': 'قبل الطلب',
                            'STOCK_QTY_AFTER':  'بعد الطلب',
                            'REDUCED BY':       'الكمية المستهلكة',
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("مفيش تغيير في INGREDIENT لهذه البيتزا.")

                st.balloons()

            except Exception as e:
                st.error(f"Error: {e}")

    st.write("---")
    st.subheader("🧅 جدول INGREDIENT الحالي")
    try:
        ing_df = get_data("""
            SELECT i.ingredient_id, i.ingredient_name, ir.stock_qty, ir.reorder_level,
                   CASE WHEN ir.stock_qty <= ir.reorder_level THEN 'LOW' ELSE 'OK' END AS status
            FROM INVENTORY_REFINED ir
            JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
            ORDER BY ir.stock_qty ASC
        """)
        if not ing_df.empty:
            def highlight_ing(row):
                return ['background-color: #ffcccc'] * len(row) if row['STATUS'] == 'LOW' else [''] * len(row)
            st.dataframe(ing_df.style.apply(highlight_ing, axis=1), use_container_width=True)
            low_ing = ing_df[ing_df['STATUS'] == 'LOW']
            if not low_ing.empty:
                st.warning(f"⚠️ {len(low_ing)} مكوّن وصل للحد الأدنى!")
            else:
                st.success("✅ المخزون كافي.")
    except Exception as e:
        st.error(f"Error loading INGREDIENT: {e}")

# ════════════════════════════════════════════
#  INVENTORY MONITOR
# ════════════════════════════════════════════
elif choice == "Inventory Monitor":
    st.subheader("📦 Live Inventory Monitor")
    st.info("The Trigger will reduce INVENTORY_FROM_PIZZA_SALES and INVENTORY_REFINED automatically!")

    # ══ عرض تأثير آخر طلب من Add Pizza Sale لو موجود ══
    if st.session_state['last_order_impact']:
        impact = st.session_state['last_order_impact']
        with st.expander(
            f"🔔 تأثير آخر طلب — {impact['pizza_name']} × {impact['quantity']} ({impact['size']}) — الساعة {impact['timestamp']}",
            expanded=True
        ):
            # ── INVENTORY_FROM_PIZZA_SALES ──
            st.markdown("#### 📦 تأثير على INVENTORY_FROM_PIZZA_SALES")
            if not impact['changed_ps'].empty:
                st.dataframe(
                    impact['changed_ps'][['INGREDIENT_NAME', 'CURRENT_STOCK_QTY_BEFORE', 'CURRENT_STOCK_QTY_AFTER', 'REDUCED BY']].rename(columns={
                        'INGREDIENT_NAME':          'المكوّن',
                        'CURRENT_STOCK_QTY_BEFORE': 'قبل الطلب',
                        'CURRENT_STOCK_QTY_AFTER':  'بعد الطلب',
                        'REDUCED BY':               'الكمية المستهلكة',
                    }),
                    use_container_width=True
                )
            else:
                st.info("مفيش تغيير في INVENTORY_FROM_PIZZA_SALES.")

            st.divider()

            # ── INVENTORY_REFINED ──
            st.markdown("#### 📊 تأثير على INVENTORY_REFINED")
            if not impact['changed_ref'].empty:
                st.dataframe(
                    impact['changed_ref'][['INGREDIENT_NAME', 'STOCK_QTY_BEFORE', 'STOCK_QTY_AFTER', 'REDUCED BY']].rename(columns={
                        'INGREDIENT_NAME':  'المكوّن',
                        'STOCK_QTY_BEFORE': 'قبل الطلب',
                        'STOCK_QTY_AFTER':  'بعد الطلب',
                        'REDUCED BY':       'الكمية المستهلكة',
                    }),
                    use_container_width=True
                )
            else:
                st.info("مفيش تغيير في INVENTORY_REFINED.")

        st.write("---")

    try:
        orders_df_mon = get_data("SELECT order_id FROM ORDERS_REFINED ORDER BY order_id DESC")
        menu_df_mon   = get_data("SELECT menu_item_id, p_name, p_size, unit_price, ingredients_list FROM MENU_ITEM_REFINED")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        order_id_mon = st.selectbox(
            "Select Order:",
            orders_df_mon['ORDER_ID'].tolist() if not orders_df_mon.empty else [],
            key="mon_order"
        )
        quantity_mon = st.number_input("Quantity", min_value=1, max_value=50, value=1, key="mon_qty")

    with col2:
        available_sizes_mon = sorted(menu_df_mon['P_SIZE'].dropna().unique().tolist()) if not menu_df_mon.empty else []
        size_labels_mon  = {'L': 'Large (L)', 'M': 'Medium (M)', 'S': 'Small (S)'}
        size_display_mon = [size_labels_mon.get(s, s) for s in available_sizes_mon]
        size_map_mon     = {size_labels_mon.get(s, s): s for s in available_sizes_mon}

        selected_size_display_mon = st.selectbox("Pizza Size:", size_display_mon if size_display_mon else ["No sizes available"], key="mon_size")
        selected_size_mon = size_map_mon.get(selected_size_display_mon, None)

        filtered_menu_mon = menu_df_mon[menu_df_mon['P_SIZE'] == selected_size_mon] if selected_size_mon and not menu_df_mon.empty else menu_df_mon
        menu_options_mon  = filtered_menu_mon['P_NAME'].tolist() if not filtered_menu_mon.empty else []
        selected_pizza_mon = st.selectbox("Select Pizza:", menu_options_mon, key="mon_pizza")

    if selected_pizza_mon and not filtered_menu_mon.empty:
        pizza_row_mon = filtered_menu_mon[filtered_menu_mon['P_NAME'] == selected_pizza_mon].iloc[0]
        st.write("---")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Unit Price", f"${pizza_row_mon['UNIT_PRICE']:.2f}")
        col_b.metric("Size", pizza_row_mon['P_SIZE'])
        col_c.metric("Total", f"${pizza_row_mon['UNIT_PRICE'] * quantity_mon:.2f}")
        st.caption(f"Ingredients: {pizza_row_mon['INGREDIENTS_LIST']}")

    if st.button("Confirm Order and Reduce Inventory", type="primary", key="mon_btn"):
        if selected_pizza_mon and not filtered_menu_mon.empty:
            pizza_row_mon = filtered_menu_mon[filtered_menu_mon['P_NAME'] == selected_pizza_mon].iloc[0]

            try:
                max_id_df  = get_data("SELECT NVL(MAX(pizza_id), 0) + 1 AS new_id FROM PIZZA_SALES")
                new_pizza_id = int(max_id_df.iloc[0]['NEW_ID'])
            except Exception:
                new_pizza_id = 1

            pizza_data_mon = {
                'pizza_id':          new_pizza_id,
                'order_id':          int(order_id_mon),
                'pizza_name_id':     str(pizza_row_mon['MENU_ITEM_ID']),
                'quantity':          int(quantity_mon),
                'order_date':        date.today(),
                'order_time':        datetime.now().strftime('%H:%M:%S'),
                'unit_price':        float(pizza_row_mon['UNIT_PRICE']),
                'total_price':       float(pizza_row_mon['UNIT_PRICE']) * int(quantity_mon),
                'pizza_size':        str(pizza_row_mon['P_SIZE']),
                'pizza_category':    'Pizza',
                'pizza_ingredients': str(pizza_row_mon['INGREDIENTS_LIST']),
                'pizza_name':        str(pizza_row_mon['P_NAME']),
            }

            inv_ps_before  = get_data("SELECT ingredient_name, current_stock_qty FROM INVENTORY_FROM_PIZZA_SALES")
            inv_ref_before = get_data("""
                SELECT i.ingredient_name, ir.stock_qty
                FROM INVENTORY_REFINED ir
                JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
            """)

            try:
                insert_pizza_sale(pizza_data_mon)
                get_data.clear()

                inv_ps_after  = get_data("SELECT ingredient_name, current_stock_qty FROM INVENTORY_FROM_PIZZA_SALES")
                inv_ref_after = get_data("""
                    SELECT i.ingredient_name, ir.stock_qty
                    FROM INVENTORY_REFINED ir
                    JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
                """)

                st.success(f"✅ Added {quantity_mon}x {selected_pizza_mon} successfully!")

                merged_ps  = inv_ps_before.merge(inv_ps_after, on='INGREDIENT_NAME', suffixes=('_BEFORE', '_AFTER'))
                changed_ps = merged_ps[merged_ps['CURRENT_STOCK_QTY_BEFORE'] != merged_ps['CURRENT_STOCK_QTY_AFTER']].copy()
                changed_ps['REDUCED BY'] = changed_ps['CURRENT_STOCK_QTY_BEFORE'] - changed_ps['CURRENT_STOCK_QTY_AFTER']

                merged_ref  = inv_ref_before.merge(inv_ref_after, on='INGREDIENT_NAME', suffixes=('_BEFORE', '_AFTER'))
                changed_ref = merged_ref[merged_ref['STOCK_QTY_BEFORE'] != merged_ref['STOCK_QTY_AFTER']].copy()
                changed_ref['REDUCED BY'] = changed_ref['STOCK_QTY_BEFORE'] - changed_ref['STOCK_QTY_AFTER']

                # ══ تحديث session_state بالطلب الجديد من Inventory Monitor برضو ══
                st.session_state['last_order_impact'] = {
                    'pizza_name':  str(pizza_row_mon['P_NAME']),
                    'quantity':    int(quantity_mon),
                    'size':        str(pizza_row_mon['P_SIZE']),
                    'timestamp':   datetime.now().strftime('%H:%M:%S'),
                    'changed_ing': changed_ref.rename(columns={'STOCK_QTY_BEFORE': 'STOCK_QTY_BEFORE', 'STOCK_QTY_AFTER': 'STOCK_QTY_AFTER'}).copy(),
                    'changed_ps':  changed_ps.copy(),
                    'changed_ref': changed_ref.copy(),
                }

                st.write("### 📉 تأثير على INVENTORY_FROM_PIZZA_SALES")
                if not changed_ps.empty:
                    st.dataframe(
                        changed_ps[['INGREDIENT_NAME', 'CURRENT_STOCK_QTY_BEFORE', 'CURRENT_STOCK_QTY_AFTER', 'REDUCED BY']].rename(columns={
                            'INGREDIENT_NAME':          'المكوّن',
                            'CURRENT_STOCK_QTY_BEFORE': 'قبل الطلب',
                            'CURRENT_STOCK_QTY_AFTER':  'بعد الطلب',
                            'REDUCED BY':               'الكمية المستهلكة',
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("مفيش تغيير في INVENTORY_FROM_PIZZA_SALES.")

                st.write("### 📉 تأثير على INVENTORY_REFINED")
                if not changed_ref.empty:
                    st.dataframe(
                        changed_ref[['INGREDIENT_NAME', 'STOCK_QTY_BEFORE', 'STOCK_QTY_AFTER', 'REDUCED BY']].rename(columns={
                            'INGREDIENT_NAME':  'المكوّن',
                            'STOCK_QTY_BEFORE': 'قبل الطلب',
                            'STOCK_QTY_AFTER':  'بعد الطلب',
                            'REDUCED BY':       'الكمية المستهلكة',
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("مفيش تغيير في INVENTORY_REFINED.")

                st.balloons()

            except Exception as e:
                st.error(f"Error: {e}")

    st.write("---")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### 📊 INVENTORY_FROM_PIZZA_SALES")
        try:
            df_ps = get_data("SELECT * FROM INVENTORY_FROM_PIZZA_SALES ORDER BY current_stock_qty ASC")
            if not df_ps.empty:
                def highlight_ps(row):
                    return ['background-color: #ffcccc'] * len(row) if row['CURRENT_STOCK_QTY'] <= row['REORDER_LEVEL'] else [''] * len(row)
                st.dataframe(df_ps.style.apply(highlight_ps, axis=1), use_container_width=True)
                low_ps = df_ps[df_ps['CURRENT_STOCK_QTY'] <= df_ps['REORDER_LEVEL']]
                if not low_ps.empty:
                    st.warning(f"⚠️ {len(low_ps)} مكوّن وصل للحد الأدنى!")
                else:
                    st.success("✅ المخزون كافي.")
        except Exception as e:
            st.error(f"Error: {e}")

    with col2:
        st.write("### 📊 INVENTORY_REFINED")
        try:
            df_ref = get_data("""
                SELECT i.ingredient_name, ir.stock_qty, ir.reorder_level,
                       CASE WHEN ir.stock_qty <= ir.reorder_level THEN 'LOW' ELSE 'OK' END AS status
                FROM INVENTORY_REFINED ir
                JOIN INGREDIENT i ON ir.ingredient_id = i.ingredient_id
                ORDER BY ir.stock_qty ASC
            """)
            if not df_ref.empty:
                def highlight_ref(row):
                    return ['background-color: #ffcccc'] * len(row) if row['STATUS'] == 'LOW' else [''] * len(row)
                st.dataframe(df_ref.style.apply(highlight_ref, axis=1), use_container_width=True)
                low_ref = df_ref[df_ref['STATUS'] == 'LOW']
                if not low_ref.empty:
                    st.warning(f"⚠️ {len(low_ref)} مكوّن وصل للحد الأدنى!")
                else:
                    st.success("✅ المخزون كافي.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("🔄 Refresh Now"):
        get_data.clear()
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Refresh App"):
    get_data.clear()
    st.rerun()
