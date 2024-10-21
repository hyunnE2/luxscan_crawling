import pymysql
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 데이터베이스 설정 (DB 자격 증명은 .env 파일에서 로드됨)
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 데이터베이스 연결 함수
def get_db_connection():
    """
    데이터베이스에 연결을 설정합니다.
    """
    return pymysql.connect(**DB_CONFIG)

# 마지막으로 처리된 psh_id를 가져오는 함수
def get_last_processed_psh_id(connection):
    """
    config 테이블에서 마지막으로 처리된 psh_id를 가져옵니다.
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT cfg_value FROM config WHERE cfg_key = 'last_processed_psh_id'")
        result = cursor.fetchone()
        return int(result['cfg_value']) if result else 0

# 마지막으로 처리된 psh_id를 저장하는 함수
def save_last_processed_psh_id(connection, psh_id):
    """
    config 테이블에 마지막으로 처리된 psh_id를 저장합니다.
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            INSERT INTO config (cfg_key, cfg_value)
            VALUES ('last_processed_psh_id', %s)
            ON DUPLICATE KEY UPDATE cfg_value = VALUES(cfg_value)
        """, (str(psh_id),))
        connection.commit()

# 배치 데이터를 가져오는 함수
def fetch_batch_data(connection, last_psh_id, batch_size=300):
    """
    product_sell_history 테이블에서 지정된 배치 크기만큼 데이터를 가져옵니다.
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            SELECT psh_id, p_id, psh_option, psh_price, DATE(psh_sold_datetime) AS sold_date
            FROM product_sell_history
            WHERE psh_id > %s AND psh_sold_datetime IS NOT NULL
            ORDER BY psh_id ASC
            LIMIT %s
        """
        cursor.execute(query, (last_psh_id, batch_size))
        return cursor.fetchall()

# 일별 데이터를 집계하는 함수
def aggregate_daily_data(batch_data):
    """
    배치 데이터를 사용하여 일별 통계 데이터를 집계합니다.
    """
    daily_stats = {}
    for record in batch_data:
        key = (record['sold_date'], record['p_id'], record['psh_option'])
        if key not in daily_stats:
            daily_stats[key] = {
                'min_price': record['psh_price'],
                'max_price': record['psh_price'],
                'total_price': record['psh_price'],
                'total_sales': 1
            }
        else:
            daily_stats[key]['min_price'] = min(daily_stats[key]['min_price'], record['psh_price'])
            daily_stats[key]['max_price'] = max(daily_stats[key]['max_price'], record['psh_price'])
            daily_stats[key]['total_price'] += record['psh_price']
            daily_stats[key]['total_sales'] += 1

    for key in daily_stats:
        daily_stats[key]['avg_price'] = daily_stats[key]['total_price'] / daily_stats[key]['total_sales']

    return daily_stats

# 일별 통계 데이터를 데이터베이스에 업데이트하는 함수
def update_daily_statistics(connection, daily_stats):
    """
    데이터베이스에 일별 통계 데이터를 삽입하거나 업데이트합니다.
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        for (stat_date, p_id, ps_option), stats in daily_stats.items():
            cursor.execute("""
                INSERT INTO product_daily_statistics 
                (ps_stat_date, p_id, ps_option, ps_min_price, ps_max_price, ps_avg_price, ps_total_sales)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    ps_min_price = LEAST(ps_min_price, VALUES(ps_min_price)),
                    ps_max_price = GREATEST(ps_max_price, VALUES(ps_max_price)),
                    ps_avg_price = (ps_avg_price * ps_total_sales + VALUES(ps_avg_price) * VALUES(ps_total_sales)) / (ps_total_sales + VALUES(ps_total_sales)),
                    ps_total_sales = ps_total_sales + VALUES(ps_total_sales);
            """, (
                stat_date, p_id, ps_option, 
                stats['min_price'], stats['max_price'], 
                stats['avg_price'], stats['total_sales']
            ))
        connection.commit()

# 월별 데이터를 집계하는 함수
def aggregate_monthly_data(connection):
    """
    일별 통계 데이터를 바탕으로 월별 통계 데이터를 집계하여 업데이트합니다.
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        query = """
            INSERT INTO product_monthly_statistics (ps_stat_month, p_id, ps_option, ps_min_price, ps_max_price, ps_avg_price, ps_total_sales)
            SELECT 
                DATE_FORMAT(ps_stat_date, '%Y-%m') AS stat_month,
                p_id,
                ps_option,
                MIN(ps_min_price) AS min_price,
                MAX(ps_max_price) AS max_price,
                AVG(ps_avg_price) AS avg_price,
                SUM(ps_total_sales) AS total_sales
            FROM product_daily_statistics
            GROUP BY stat_month, p_id, ps_option
            ON DUPLICATE KEY UPDATE
                ps_min_price = LEAST(ps_min_price, VALUES(ps_min_price)),
                ps_max_price = GREATEST(ps_max_price, VALUES(ps_max_price)),
                ps_avg_price = (ps_avg_price * ps_total_sales + VALUES(ps_avg_price) * VALUES(ps_total_sales)) / (ps_total_sales + VALUES(ps_total_sales)),
                ps_total_sales = ps_total_sales + VALUES(ps_total_sales);
        """
        cursor.execute(query)
        connection.commit()

# 메인 함수
def main():
    """
    메인 실행 함수로서, 데이터베이스에서 배치 데이터를 가져오고, 일별 통계를 집계하고 업데이트하며, 월별 통계를 업데이트합니다.
    """
    connection = get_db_connection()

    try:
        # 마지막으로 처리된 psh_id를 가져옵니다.
        last_psh_id = get_last_processed_psh_id(connection)
        
        while True:
            # 배치 데이터를 가져옵니다.
            batch_data = fetch_batch_data(connection, last_psh_id, batch_size=300)
            if not batch_data:
                break

            # 일별 통계 데이터 집계
            daily_stats = aggregate_daily_data(batch_data)
            # 데이터베이스에 일별 통계 데이터 업데이트
            update_daily_statistics(connection, daily_stats)

            # 마지막으로 처리된 psh_id를 업데이트합니다.
            last_psh_id = batch_data[-1]['psh_id']
            save_last_processed_psh_id(connection, last_psh_id)

        # 월별 통계 데이터 집계
        aggregate_monthly_data(connection)

    finally:
        connection.close()

# 메인 함수 실행
if __name__ == "__main__":
    main()
