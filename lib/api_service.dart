import 'dart:convert';
import 'package:http/http.dart' as http;
import 'message.dart';

class ApiService {
  final String baseUrl;

  ApiService({required this.baseUrl});

  Future<List<Message>> fetchMessages() async {
    final response = await http.get(Uri.parse('$baseUrl/messages'));

    if (response.statusCode == 200) {
      final List<dynamic> jsonList = jsonDecode(response.body);
      return jsonList.map((json) => Message.fromJson(json)).toList();
    } else {
      throw Exception('Failed to fetch messages');
    }
  }

  Future<void> sendMessage(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/messages'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to send message');
    }
  }
}
