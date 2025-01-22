<?php
// Get chat id https://api.telegram.org/bot7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU/getUpdates
$apiToken = "7541502749:AAHO0ro39ZhMhS8gHFNy9DeKcaE5Ux7CUyU"; // https://web.telegram.org/k/#@itdtestt_bot
$chatId = "5696892272";
// 2. Gọi API bonds để lấy dữ liệu JSON
$apiUrl = "https://realtime-api.ape.bond/bonds";
$jsonData = file_get_contents($apiUrl);
$data = json_decode($jsonData, true);

if (!$data || !isset($data['bonds'])) {
    die("Không lấy được dữ liệu từ API.");
}

// Lọc 10 bond có % bonus cao nhất
$bonds = $data['bonds'];
usort($bonds, function ($a, $b) {
    return $b['bonus'] <=> $a['bonus'];
});
$top10Bonds = array_slice($bonds, 0, 10);

$textMessage = "🚀 **Danh sách 10 bond có % bonus cao nhất** 🚀\n\n";
$textMessage .= "*Thông tin các bond:* \n";
foreach ($top10Bonds as $index => $bond) {
    $bondName = $bond['principalTokenName'] . "-" . $bond['payoutTokenName'];
    $contractAddress = $bond['principalToken'];
    $dateTime = date('Y-m-d H:i:s', time()); // Thời gian hiện tại
    $bonus = number_format($bond['bonus'], 2) . '%';
    $minPrice = number_format($bond['trueBillPrice'] / pow(10, $bond['principalTokenDecimals']), 2);
    $maxPrice = number_format($bond['maxTotalPayout'] / pow(10, $bond['payoutTokenDecimals']), 2);
    $maxBuy = number_format($bond['maxPayout'] / pow(10, $bond['payoutTokenDecimals']), 2);

    $textMessage .= "Bond #" . ($index + 1) . ":\n";  // Đảm bảo nối chuỗi đúng cách
    $textMessage .= "➡️ **Bond Name**: $bondName\n";
    $textMessage .= "➡️ **Contract Address**: $contractAddress\n";
    $textMessage .= "➡️ **Date-time**: $dateTime\n";
    $textMessage .= "➡️ **Bonus**: $bonus\n";
    $textMessage .= "➡️ **Min Price**: $minPrice USDC\n";
    $textMessage .= "➡️ **Max Price**: $maxPrice GPT\n";
    $textMessage .= "➡️ **Max Buy**: $maxBuy GPT\n";
    $textMessage .= str_repeat("─", 40) . "\n";
}

// Gửi tin nhắn qua Telegram
$url = "https://api.telegram.org/bot$apiToken/sendMessage";

$data = [
    'chat_id' => $chatId,
    'text' => $textMessage,
    'parse_mode' => 'Markdown', // Dùng Markdown để định dạng
];

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);

echo "Phản hồi từ Telegram: $response";


//// MySQL connection details
//$host = "localhost";         // Host (e.g., localhost)
//$username = "admin";         // MySQL username
//$password = "admin";         // MySQL password
//$database = "infura_io";     // Database name
//$port = 3306;
//
//// Establish the connection
//$conn = new mysqli($host, $username, $password, $database);
//
//// Check the connection
//if ($conn->connect_error) {
//    die("Connection failed: " . $conn->connect_error);
//}
//echo "Connection successful!";
//
//// Example query: Show tables
//$sql = "SHOW TABLES";
//$result = $conn->query($sql);
//
//// Check if there are tables and print them
//if ($result->num_rows > 0) {
//    echo "Tables in the database:";
//    while ($row = $result->fetch_array()) {
//        echo $row[0] . "<br>";
//    }
//} else {
//    echo "No tables found in the database.";
//}
//
//// Close the connection
//$conn->close();

?>

