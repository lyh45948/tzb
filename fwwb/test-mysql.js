const mysql = require('mysql2/promise');

async function testConnection() {
  console.log('Testing MySQL connection...');
  console.log('  Host: localhost:3306');
  console.log('  User: root');
  console.log('  Database: mysql');
  console.log('');

  try {
    const connection = await mysql.createConnection({
      host: 'localhost',
      port: 3306,
      user: 'root',
      password: '1234',
      database: 'mysql'
    });

    const [rows] = await connection.execute('SELECT VERSION() as version');
    console.log('✓ MySQL connection successful!');
    console.log('  Server version:', rows[0].version);

    // Show databases
    const [dbs] = await connection.execute('SHOW DATABASES');
    console.log('\n  Available databases:');
    dbs.forEach(db => {
      console.log('    -', db.Database);
    });

    await connection.end();
  } catch (error) {
    console.error('✗ MySQL connection failed:', error.message);
    console.log('\nTroubleshooting:');
    console.log('  1. Ensure MySQL service is running (net start mysql)');
    console.log('  2. Verify credentials are correct');
    console.log('  3. Check if port 3306 is accessible');
    console.log('  4. For MySQL 8.0+, you may need to use mysql_native_password');
    console.log('\n  Try running in MySQL shell:');
    console.log('    ALTER USER \'root\'@\'localhost\' IDENTIFIED WITH mysql_native_password BY \'\';');
  }
}

testConnection();
