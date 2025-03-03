import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'LessonPage.dart';

class FileDetailPage extends StatelessWidget {
  final String fileName;

  FileDetailPage({required this.fileName});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(fileName)),
      body: FutureBuilder<String>(
        future: fetchFileContent(fileName),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          } else if (snapshot.hasError) {
            return Center(child: Text('Error loading file content'));
          } else {
            String fileContent = snapshot.data ?? 'No content available';
            return Padding(
              padding: const EdgeInsets.all(16.0),
              child: SingleChildScrollView(
                child: Text(fileContent),
              ),
            );
          }
        },
      ),
      floatingActionButton: FutureBuilder<String>(
        future: fetchFileContent(fileName),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return Container(); // Hide button if data isn't ready
          }
          String fileContent = snapshot.data ?? 'No content available';
          return FloatingActionButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => LessonPage(testText: fileContent)), // Pass text
              );
            },
            child: Icon(Icons.add), // "+" icon
            backgroundColor: Colors.deepOrange,
          );
        },
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat, // Bottom right corner
    );
  }

  Future<String> fetchFileContent(String fileName) async {
    final response = await http.get(
      Uri.parse("http://10.0.2.2:5000/get_file_content?file=$fileName"),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['text'] ?? 'No text extracted';
    } else {
      throw Exception('Failed to load file content');
    }
  }
}
