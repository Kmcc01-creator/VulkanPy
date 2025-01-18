import 'dart:convert';
import 'package:http/http.dart' as http;
import 'message.dart';

class ApiService {
  final String baseUrl;

  ApiService({required this.baseUrl});

  Future<Message> fetchMessage() async {
    final response = await http.get(Uri.parse('$baseUrl/message'));

    if (response.statusCode == 200) {
      return Message.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to fetch message');
    }
  }
}
